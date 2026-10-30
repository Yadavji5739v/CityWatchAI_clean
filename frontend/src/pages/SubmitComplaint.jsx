
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUpRight,
  AlertTriangle,
  Camera,
  CameraOff,
  Image as ImageIcon,
  LocateFixed,
  MapPin,
  ShieldCheck,
  Trash2,
  Video,
  FileCheck2,
  Users,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../lib/api";

const categoryOptions = [
  "Pothole",
  "Road Damage",
  "Garbage / Waste",
  "Drainage",
  "Water Supply",
  "Illegal Parking",
  "Road Obstruction",
  "Street Light",
  "Other Civic Issue",
];

const MAX_VIDEO_SIZE = 50 * 1024 * 1024;
const MAX_IMAGE_SIZE = 10 * 1024 * 1024;
const MAX_IMAGES = 5;

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(0)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function SubmitComplaint({ onSubmit }) {
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [category, setCategory] = useState(categoryOptions[0]);
  const [location, setLocation] = useState("");
  const [coordinates, setCoordinates] = useState(null);
  const [description, setDescription] = useState("");
  const [evidenceFiles, setEvidenceFiles] = useState([]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [locating, setLocating] = useState(false);
  const [duplicateMatches, setDuplicateMatches] = useState([]);
  const [showDuplicateWarning, setShowDuplicateWarning] = useState(false);
  const [cameraStream, setCameraStream] = useState(null);
  const [openingCamera, setOpeningCamera] = useState(false);
  const [capturingPhoto, setCapturingPhoto] = useState(false);
  const [recordingVideo, setRecordingVideo] = useState(false);
  const [cameraError, setCameraError] = useState("");

  const previewUrls = useRef(new Set());
  const cameraVideoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const videoChunksRef = useRef([]);

  useEffect(() => {
    return () => {
      previewUrls.current.forEach((url) => URL.revokeObjectURL(url));
      previewUrls.current.clear();
    };
  }, []);

  useEffect(() => {
    if (!cameraStream || !cameraVideoRef.current) return undefined;
    const video = cameraVideoRef.current;
    video.srcObject = cameraStream;
    video.play().catch(() => setCameraError("Camera preview could not start. Check camera permissions and try again."));
    return () => {
      if (mediaRecorderRef.current?.state !== "inactive") mediaRecorderRef.current?.stop();
      cameraStream.getTracks().forEach((track) => track.stop());
      if (video.srcObject === cameraStream) video.srcObject = null;
    };
  }, [cameraStream]);

  const imageCount = evidenceFiles.filter(({ file }) =>
    file.type.startsWith("image/")
  ).length;

  const videoCount = evidenceFiles.filter(({ file }) =>
    file.type.startsWith("video/")
  ).length;

  const canSubmit = useMemo(
    () =>
      Boolean(title.trim()) &&
      Boolean(location.trim()) &&
      !submitting,
    [title, location, submitting]
  );

    
async function useCurrentLocation() {
  if (!navigator.geolocation) {
    setError("Your browser does not support GPS location.");
    return;
  }

  setLocating(true);
  setError("");

  navigator.geolocation.getCurrentPosition(
    async ({ coords }) => {
      const { latitude, longitude } = coords;
      setCoordinates({ latitude, longitude });

      try {
        // Convert GPS coordinates into a readable address.
        // This requires an available reverse-geocoding service.
        const response = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}`
        );

        if (!response.ok) {
          throw new Error("Could not retrieve the address.");
        }

        const data = await response.json();

        if (data.display_name) {
          setLocation(data.display_name);
        } else {
          setError(
            "Address not found. Please enter the location manually."
          );
        }
      } catch {
        setError(
          "Could not find the address. Please enter the location manually."
        );
      } finally {
        setLocating(false);
      }
    },
    () => {
      setError(
        "Location access failed. Allow GPS access in your browser and try again."
      );
      setLocating(false);
    },
    {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 60000,
    }
  );
}


  async function startCamera() {
    setCameraError("");
    if (imageCount >= MAX_IMAGES) {
      setCameraError(`You can capture up to ${MAX_IMAGES} photos.`);
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError("Live photos require camera access over HTTPS or localhost in a supported browser.");
      return;
    }

    setOpeningCamera(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      setCameraStream(stream);
    } catch (cameraFailure) {
      setCameraError(cameraFailure?.name === "NotAllowedError"
        ? "Camera permission was denied. Allow camera access in your browser settings and try again."
        : "Could not start the camera. Check that it is available and try again.");
    } finally {
      setOpeningCamera(false);
    }
  }

  function startVideoRecording() {
    if (!cameraStream || videoCount > 0 || recordingVideo) return;
    if (!window.MediaRecorder) {
      setCameraError("Live video recording is not supported by this browser.");
      return;
    }
    try {
      const preferredType = ["video/webm;codecs=vp9", "video/webm", "video/mp4"]
        .find((type) => MediaRecorder.isTypeSupported?.(type));
      const recorder = new MediaRecorder(cameraStream, preferredType ? { mimeType: preferredType } : undefined);
      videoChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data?.size) videoChunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        setCameraError("Video recording failed. Please try again.");
        setRecordingVideo(false);
      };
      recorder.onstop = () => {
        const recordedMimeType = (recorder.mimeType || videoChunksRef.current[0]?.type || "video/webm").split(";")[0].toLowerCase();
        const mimeType = recordedMimeType === "video/mp4" ? "video/mp4" : "video/webm";
        const blob = new Blob(videoChunksRef.current, { type: mimeType });
        videoChunksRef.current = [];
        if (!blob.size) return;
        if (blob.size > MAX_VIDEO_SIZE) {
          setCameraError("The recorded video exceeds the 50 MB limit. Record a shorter video.");
          return;
        }
        const extension = mimeType === "video/mp4" ? "mp4" : "webm";
        const file = new File([blob], `citywatch-live-${Date.now()}.${extension}`, { type: mimeType });
        const preview = URL.createObjectURL(file);
        previewUrls.current.add(preview);
        setEvidenceFiles((files) => [...files.filter(({ file: existing }) => !existing.type.startsWith("video/")), { file, preview }]);
      };
      recorder.start(1000);
      mediaRecorderRef.current = recorder;
      setRecordingVideo(true);
      setCameraError("");
    } catch {
      setCameraError("Could not start video recording. Check camera access and try again.");
    }
  }

  function stopVideoRecording() {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    mediaRecorderRef.current = null;
    setRecordingVideo(false);
  }

  async function captureLivePhoto() {
    if (capturingPhoto) return;
    setCapturingPhoto(true);
    try {
    const video = cameraVideoRef.current;
    if (!video?.videoWidth || !video?.videoHeight) {
      setCameraError("Wait for the camera preview, then try again.");
      return;
    }
    if (imageCount >= MAX_IMAGES) {
      setCameraError(`You can capture up to ${MAX_IMAGES} photos.`);
      return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setCameraError("Photo capture is not supported by this browser.");
      return;
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const photoBlob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
    if (!photoBlob) {
      setCameraError("The photo could not be captured. Please try again.");
      return;
    }
    if (photoBlob.size > MAX_IMAGE_SIZE) {
      setCameraError("This photo is larger than 10 MB. Move closer or use lower camera resolution.");
      return;
    }

    const file = new File([photoBlob], `citywatch-live-${Date.now()}.jpg`, { type: "image/jpeg" });
    const preview = URL.createObjectURL(file);
    previewUrls.current.add(preview);
    setEvidenceFiles((files) => [...files, { file, preview }]);
    setCameraError("");
    if (imageCount + 1 >= MAX_IMAGES) setCameraStream(null);
    } finally {
      setCapturingPhoto(false);
    }
  }

  function removeEvidence(preview) {
    URL.revokeObjectURL(preview);
    previewUrls.current.delete(preview);

    setEvidenceFiles((files) =>
      files.filter((item) => item.preview !== preview)
    );

    setError("");
  }

  function buildSubmissionFormData(supportExistingId = null, confirmNewComplaint = false) {
    const formData = new FormData();
    formData.append("title", title.trim());
    formData.append("category", category);
    formData.append("location", location.trim());
    formData.append("description", description.trim());
    formData.append("priority", "Needs Review");
    formData.append("status", "Submitted");
    if (coordinates) {
      formData.append("latitude", String(coordinates.latitude));
      formData.append("longitude", String(coordinates.longitude));
    }
    if (supportExistingId) formData.append("support_existing_id", supportExistingId);
    if (confirmNewComplaint) formData.append("confirm_new_complaint", "true");
    for (const { file } of evidenceFiles) formData.append("evidence", file, file.name);
    return formData;
  }

  async function saveComplaint(supportExistingId = null, confirmNewComplaint = false) {
    const token = localStorage.getItem("citywatch_token");
    const response = await fetch(`${API_BASE_URL}/complaints`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: buildSubmissionFormData(supportExistingId, confirmNewComplaint),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (result.detail?.code === "duplicate_confirmation_required") {
        setDuplicateMatches(result.detail.matches || []);
        setShowDuplicateWarning(true);
        return;
      }
      throw new Error(typeof result.detail === "string" ? result.detail : "Complaint submission failed.");
    }

    if (typeof onSubmit === "function") onSubmit(result);
    navigate(`/details/${result.id}`, {
      state: { from: "/complaints", submittedComplaint: result },
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError("");
    try {
      const token = localStorage.getItem("citywatch_token");
      const response = await fetch(`${API_BASE_URL}/complaints/check-duplicates`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: buildSubmissionFormData(),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "Could not check for similar complaints.");
      if (result.matches?.length) {
        setDuplicateMatches(result.matches);
        setShowDuplicateWarning(true);
        return;
      }
      await saveComplaint();
    } catch (submitError) {
      console.error("Complaint submission error:", submitError);
      setError(submitError instanceof Error ? submitError.message : "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitAfterDuplicateChoice(supportExistingId = null, confirmNewComplaint = false) {
    setSubmitting(true);
    setError("");
    setShowDuplicateWarning(false);
    try {
      await saveComplaint(supportExistingId, confirmNewComplaint);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Submission failed. Please try again.");
      setShowDuplicateWarning(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page-stack">
      <div className="page-heading">
        <div>
          <div className="eyebrow">CITIZEN SERVICES</div>
          <h1>Report a Problem</h1>
          <p>
            Provide details and optional photo or video evidence of
            the civic issue.
          </p>
        </div>
      </div>

      <div className="form-layout">
        <form
          className="content-panel report-form"
          onSubmit={handleSubmit}
        >
          {/* PROBLEM DETAILS */}
          <div className="form-section-title">
            <span className="step-number">01</span>
            <div>
              <h2>Problem details</h2>
              <p>Describe the issue clearly.</p>
            </div>
          </div>

          <label>
            Complaint title <span className="required">*</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Large pothole near bus stop"
              required
              maxLength={120}
            />
          </label>

          <label>
            Problem category <span className="required">*</span>
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              required
            >
              {categoryOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label>
            Issue location <span className="required">*</span>
            <div className="input-with-icon">
              <MapPin size={18} />
              <input
                value={location}
                onChange={(event) => {
                  setLocation(event.target.value);
                  setCoordinates(null);
                }}
                placeholder="Road, area, ward, or landmark"
                required
                maxLength={500}
              />
            </div>
            <small>
              Enter where the civic problem is. You can also attach
              your current GPS coordinates.
            </small>
          </label>

          <button
            className="secondary-button location-button"
            type="button"
            onClick={useCurrentLocation}
            disabled={locating || submitting}
          >
            <LocateFixed size={16} />
            {locating ? "Getting location..." : "Use my current location"}
          </button>

          <label>
            Description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={4}
              maxLength={1000}
              placeholder="Explain the condition, urgency, and impact on residents."
            />
          </label>

          {/* LIVE PHOTO AND VIDEO CAPTURE */}
          <div className="form-section-title evidence-title">
            <span className="step-number">02</span>
            <div>
              <h2>Live photo or video evidence</h2>
              <p>
                Allow camera access, then capture photos or record a video. File uploads are disabled.
              </p>
            </div>
          </div>

          <section className="live-photo-panel">
            <div className="live-photo-heading">
              <span className="live-photo-icon"><Camera size={19} /></span>
              <div><strong>Camera evidence</strong><small>Camera permission is requested when you open the camera. Then choose photo or video.</small></div>
              {!cameraStream && <button type="button" className="secondary-button" onClick={startCamera} disabled={submitting || openingCamera || imageCount >= MAX_IMAGES}>
                <Camera size={16} /> {openingCamera ? "Opening camera…" : "Open camera"}
              </button>}
            </div>
            {cameraError && <div className="form-error camera-error" role="alert">{cameraError}</div>}
            {cameraStream && <div className="live-camera-view">
              <video ref={cameraVideoRef} autoPlay playsInline muted aria-label="Live camera preview" />
              <div className="live-camera-actions">
                <button type="button" className="primary-button" onClick={captureLivePhoto} disabled={submitting || capturingPhoto || imageCount >= MAX_IMAGES || recordingVideo}><Camera size={16} /> {capturingPhoto ? "Capturing…" : "Take photo"}</button>
                {videoCount === 0 && (recordingVideo
                  ? <button type="button" className="secondary-button" onClick={stopVideoRecording} disabled={submitting}><Video size={16} /> Stop recording</button>
                  : <button type="button" className="secondary-button" onClick={startVideoRecording} disabled={submitting}><Video size={16} /> Record video</button>)}
                <button type="button" className="secondary-button" onClick={() => { if (recordingVideo) stopVideoRecording(); setCameraStream(null); }} disabled={submitting || recordingVideo}><CameraOff size={16} /> Close camera</button>
              </div>
            </div>}
          </section>

          {/* FILE COUNTS */}
          <div className="evidence-count-row">
            <span>
              <ImageIcon size={15} />
              Images: {imageCount}/{MAX_IMAGES}
            </span>

            <span>
              <Video size={15} />
              Videos: {videoCount}/1
            </span>
          </div>

          {/* SELECTED FILE PREVIEWS */}
          {evidenceFiles.length > 0 && (
            <div className="evidence-preview-section">
              <div className="evidence-preview-heading">
                <FileCheck2 size={18} />
                <h3>Selected evidence</h3>
                <span>{evidenceFiles.length} file(s)</span>
              </div>

              <div className="evidence-preview-grid">
                {evidenceFiles.map(({ file, preview }) => {
                  const isVideo = file.type.startsWith("video/");

                  return (
                    <article
                      className="video-preview-card"
                      key={preview}
                    >
                      <div className="evidence-preview-media">
                        {isVideo ? (
                          <video
                            src={preview}
                            controls
                            playsInline
                            preload="metadata"
                            onError={() => setCameraError("The recorded video could not be played in this browser. Try recording again.")}
                          />
                        ) : (
                          <img
                            src={preview}
                            alt={`Evidence: ${file.name}`}
                          />
                        )}
                      </div>

                      <div className="video-file-info">
                        {isVideo ? (
                          <Video size={17} />
                        ) : (
                          <ImageIcon size={17} />
                        )}

                        <div className="evidence-file-text">
                          <span title={file.name}>{file.name}</span>
                          <small>{formatFileSize(file.size)}</small>
                        </div>

                        <button
                          type="button"
                          className="icon-button danger-icon"
                          onClick={() => removeEvidence(preview)}
                          disabled={submitting}
                          aria-label={`Remove ${file.name}`}
                          title="Remove file"
                        >
                          <Trash2 size={17} />
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          )}

          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}

          {/* FORM ACTIONS */}
          <div className="form-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => navigate("/")}
              disabled={submitting}
            >
              Cancel
            </button>

            <button
              className="primary-button"
              type="submit"
              disabled={!canSubmit}
            >
              {submitting ? "Submitting..." : "Submit Complaint"}
              <ArrowUpRight size={17} />
            </button>
          </div>
        </form>

        {/* RIGHT SIDEBAR */}
        <aside className="form-aside">
          <div className="aside-card">
            <ShieldCheck size={25} />

            <h3>What happens next?</h3>

            <ol className="timeline">
              <li>
                <strong>Submission</strong>
                <span>Your report is recorded.</span>
              </li>

              <li>
                <strong>AI analysis</strong>
                <span>
                  Supported road evidence is classified; unsupported
                  categories stay with human review.
                </span>
              </li>

              <li>
                <strong>Review</strong>
                <span>
                  Officers validate the issue and assign action.
                </span>
              </li>

              <li>
                <strong>Resolution</strong>
                <span>
                  Track updates until closure or reopening.
                </span>
              </li>
            </ol>
          </div>

          <div className="privacy-note">
            <ShieldCheck size={17} />
            <span>
              Photos and videos recorded here are attached to this complaint. Camera file uploads are disabled.
            </span>
          </div>
        </aside>
      </div>
      {showDuplicateWarning && (
        <div
          className="duplicate-warning-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !submitting) setShowDuplicateWarning(false);
          }}
        >
          <section className="duplicate-warning-dialog" role="dialog" aria-modal="true" aria-labelledby="duplicate-warning-title">
            <header className="duplicate-warning-header">
              <span className="duplicate-warning-icon"><AlertTriangle size={21} /></span>
              <div>
                <h2 id="duplicate-warning-title">A similar complaint already exists!</h2>
                <p>Review the matching reports. Support an existing issue or submit this as a separate problem.</p>
              </div>
              <button type="button" className="icon-button" onClick={() => setShowDuplicateWarning(false)} disabled={submitting} aria-label="Close warning"><X size={18} /></button>
            </header>

            <div className="duplicate-match-list">
              {duplicateMatches.map((match) => (
                <article className="duplicate-match-card" key={match.id}>
                  {match.image_preview ? (
                    <img className="duplicate-match-image" src={match.image_preview} alt={`Existing evidence for ${match.title}`} />
                  ) : (
                    <div className="duplicate-match-image duplicate-match-image-empty"><ImageIcon size={22} />No image</div>
                  )}
                  <div className="duplicate-match-body">
                    <div className="duplicate-match-id">{match.id}</div>
                    <h3>{match.title}</h3>
                    <p><MapPin size={14} />{match.location || "Location not provided"}</p>
                    <div className="duplicate-match-meta">
                      <span>Status: <strong>{match.status}</strong></span>
                      <span><Users size={14} />{match.report_count} {match.report_count === 1 ? "citizen" : "citizens"} reported</span>
                    </div>
                    <button className="primary-button small" type="button" disabled={submitting} onClick={() => submitAfterDuplicateChoice(match.id)}>
                      Support Existing Complaint
                    </button>
                  </div>
                </article>
              ))}
            </div>

            {error && <div className="form-error duplicate-warning-error" role="alert">{error}</div>}
            <footer className="duplicate-warning-actions">
              <button type="button" className="secondary-button" onClick={() => setShowDuplicateWarning(false)} disabled={submitting}>Keep editing</button>
              <button type="button" className="secondary-button" onClick={() => submitAfterDuplicateChoice(null, true)} disabled={submitting}>
                {submitting ? "Submitting..." : "Submit as New Complaint"}
              </button>
            </footer>
          </section>
        </div>
      )}
    </main>
  );
}
