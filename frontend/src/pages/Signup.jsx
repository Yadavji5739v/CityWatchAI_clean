
import { useState } from "react";
import { Link } from "react-router-dom";
import { UserRound, Mail, LockKeyhole, UserPlus } from "lucide-react";
import "./Auth.css";

export default function Signup({ onSignup }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      if (typeof onSignup !== "function") {
        throw new Error("Account creation is not configured. Please try again later.");
      }
      await onSignup({
        full_name: name.trim(),
        email: email.trim(),
        mobile: mobile.trim(),
        password,
      });
    } catch (signupError) {
      setError(
        signupError instanceof Error
          ? signupError.message
          : "Account creation failed. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-heading">
          <div className="auth-brand-icon">
            <UserPlus size={23} />
          </div>
          <h1>Create an Account</h1>
          <p>Join the CityWatch AI community</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="signup-name">Full Name</label>
          <div className="auth-input-wrap">
            <UserRound size={16} />
            <input
              id="signup-name"
              name="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your full name"
              autoComplete="name"
              required
            />
          </div>

          <label htmlFor="signup-email">Email Address</label>
          <div className="auth-input-wrap">
            <Mail size={16} />
            <input
              id="signup-email"
              name="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email address"
              autoComplete="email"
              required
            />
          </div>

          <label htmlFor="signup-mobile">Mobile Number</label>
          <div className="auth-input-wrap">
            <input
              id="signup-mobile"
              name="mobile"
              type="tel"
              value={mobile}
              onChange={(e) => setMobile(e.target.value)}
              placeholder="Enter your mobile number"
              autoComplete="tel"
              required
            />
          </div>

          <label htmlFor="signup-password">Password</label>
          <div className="auth-input-wrap">
            <LockKeyhole size={16} />
            <input
              id="signup-password"
              name="new-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Create a password"
              autoComplete="new-password"
              minLength={8}
              required
            />
          </div>

          <label htmlFor="signup-confirm">Confirm Password</label>
          <div className="auth-input-wrap">
            <LockKeyhole size={16} />
            <input
              id="signup-confirm"
              name="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm your password"
              autoComplete="new-password"
              minLength={8}
              required
            />
          </div>

          {error && (
            <p className="auth-error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="auth-primary-button" disabled={submitting}>
            {submitting ? "Creating account..." : "Create Account"} <UserPlus size={17} />
          </button>
        </form>

        <p className="auth-switch">
          Already have an account?{" "}
          <Link to="/login" className="auth-text-button">
            Log in
          </Link>
        </p>
      </section>
    </main>
  );
}
