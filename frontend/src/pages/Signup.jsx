
import { useState } from "react";
import { Link } from "react-router-dom";
import { UserRound, Mail, LockKeyhole, UserPlus } from "lucide-react";
import "./Auth.css";

export default function Signup() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setError(
      "The signup form is ready, but registration must be connected to your backend API."
    );
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

          <button type="submit" className="auth-primary-button">
            Create Account <UserPlus size={17} />
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
