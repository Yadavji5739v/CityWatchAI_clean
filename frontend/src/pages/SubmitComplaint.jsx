
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUpRight,
  Image as ImageIcon,
  LocateFixed,
  MapPin,
  ShieldCheck,
  Trash2,
  UploadCloud,
  Video,
  FileCheck2,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

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

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

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
  const [description, setDescription] = useState("");
  const [evidenceFiles, setEvidenceFiles] = useState([]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [locating, setLocating] = useState(false);

  const previewUrls = useRef(new Set());

  useEffect(() => {
    return () => {
      previewUrls.current.forEach((url) => URL.revokeObjectURL(url));
      previewUrls.current.clear();
    };
  }, []);

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


  function handleEvidenceSelect(event) {
    const selectedFiles = Array.from(event.target.files || []);

    let currentImages = evidenceFiles.filter(({ file }) =>
      file.type.startsWith("image/")
    ).length;

    let hasVideo = evidenceFiles.some(({ file }) =>
      file.type.startsWith("video/")
    );

    const accepted = [];
    let validationError = "";

    for (const file of selectedFiles) {
      if (file.type.startsWith("image/")) {
        if (currentImages >= MAX_IMAGES) {
          validationError = `You can upload a maximum of ${MAX_IMAGES} images.`;
          continue;
        }

        if (file.size > MAX_IMAGE_SIZE) {
          validationError = `${file.name} exceeds the 10 MB image limit.`;
          continue;
        }

        currentImages += 1;

        accepted.push({
          file,
          preview: URL.createObjectURL(file),
        });
      } else if (file.type.startsWith("video/")) {
        if (hasVideo) {
          validationError = "You can upload only one video.";
          continue;
        }

        if (file.size > MAX_VIDEO_SIZE) {
          validationError = `${file.name} exceeds the 50 MB video limit.`;
          continue;
        }

        hasVideo = true;

        accepted.push({
          file,
          preview: URL.createObjectURL(file),
        });
      } else {
        validationError = `${file.name} is not a supported image or video.`;
      }
    }

    accepted.forEach(({ preview }) => {
      previewUrls.current.add(preview);
    });

    if (accepted.length > 0) {
      setEvidenceFiles((files) => [...files, ...accepted]);
    }

    setError(validationError);
    event.target.value = "";
  }

  function removeEvidence(preview) {
    URL.revokeObjectURL(preview);
    previewUrls.current.delete(preview);

    setEvidenceFiles((files) =>
      files.filter((item) => item.preview !== preview)
    );

    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!canSubmit) return;

    setSubmitting(true);
    setError("");

    try {
      const formData = new FormData();

      formData.append("title", title.trim());
      formData.append("category", category);
      formData.append("location", location.trim());
      formData.append("description", description.trim());
      formData.append("priority", "Needs Review");
      formData.append("status", "Submitted");

      // Images and videos are sent using the existing "evidence" field.
      for (const { file } of evidenceFiles) {
        formData.append("evidence", file, file.name);
      }

      const token = localStorage.getItem("citywatch_token");

      const headers = token
        ? { Authorization: `Bearer ${token}` }
        : {};

      const response = await fetch(`${API_BASE_URL}/complaints`, {
        method: "POST",
        headers,
        body: formData,
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(
          message || "Complaint submission failed."
        );
      }

      const savedComplaint = await response.json();

      if (typeof onSubmit === "function") {
        onSubmit(savedComplaint);
      }

      navigate(`/details/${savedComplaint.id}`, {
        state: {
          from: "/complaints",
          submittedComplaint: savedComplaint,
        },
      });
    } catch (submitError) {
      console.error("Complaint submission error:", submitError);

      const message =
        submitError instanceof Error
          ? submitError.message
          : "Submission failed. Please try again.";

      setError(message);
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
                onChange={(event) => setLocation(event.target.value)}
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

          {/* SINGLE COMBINED EVIDENCE UPLOAD */}
          <div className="form-section-title evidence-title">
            <span className="step-number">02</span>
            <div>
              <h2>Photo or video evidence</h2>
              <p>
                Upload up to five images and one video using a single
                upload area.
              </p>
            </div>
          </div>

          <label className="upload-zone single-upload-zone">
            <UploadCloud size={34} />

            <strong>Upload Photos or Videos</strong>

            <span>
              Click here to select images and videos from your device.
            </span>

            <span className="upload-format-note">
              Images: JPEG, PNG, WebP or GIF · Up to 5 images,
              10 MB each
            </span>

            <span className="upload-format-note">
              Videos: MP4, MOV, AVI, MKV or WebM · 1 video,
              maximum 50 MB
            </span>

            <span className="upload-select-button">
              Browse Files
            </span>

            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif,video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm"
              multiple
              onChange={handleEvidenceSelect}
              disabled={submitting}
              hidden
            />
          </label>

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
                            preload="metadata"
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
              Only upload evidence you are authorized to share.
            </span>
          </div>
        </aside>
      </div>
    </main>
  );
}
