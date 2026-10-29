
// import { useState } from "react";
// import {
//   ArrowRight,
//   Eye,
//   EyeOff,
//   LockKeyhole,
//   Mail,
//   ShieldCheck,
// } from "lucide-react";
// import "./Auth.css";

// export default function Login({ onLogin, onGoogleLogin, onSignup }) {
//   const [email, setEmail] = useState("");
//   const [password, setPassword] = useState("");
//   const [rememberMe, setRememberMe] = useState(true);
//   const [showPassword, setShowPassword] = useState(false);
//   const [error, setError] = useState("");
//   const [submitting, setSubmitting] = useState(false);

//   async function handleSubmit(event) {
//     event.preventDefault();
//     setError("");

//     if (!email.trim() || !password) {
//       setError("Please enter your email and password.");
//       return;
//     }

//     setSubmitting(true);

//     try {
//       // Your authentication handler must support email-based login.
//       await onLogin(email.trim(), password, { rememberMe });
//     } catch (loginError) {
//       setError(
//         loginError instanceof Error
//           ? loginError.message
//           : "Login failed. Please try again."
//       );
//     } finally {
//       setSubmitting(false);
//     }
//   }

//   async function handleGoogleLogin() {
//     setError("");

//     if (!onGoogleLogin) {
//       setError("Google sign-in has not been configured yet.");
//       return;
//     }

//     try {
//       await onGoogleLogin();
//     } catch (loginError) {
//       setError(
//         loginError instanceof Error
//           ? loginError.message
//           : "Google sign-in failed. Please try again."
//       );
//     }
//   }

//   return (
//     <main className="auth-page">
//       <section className="auth-card">
//         <div className="auth-heading">
//           <div className="auth-brand-icon">
//             <ShieldCheck size={23} />
//           </div>

//           <h1>Log in to Your Account</h1>
//           <p>Continue to CityWatch AI</p>
//         </div>

//         <button
//           type="button"
//           className="auth-google-button"
//           onClick={handleGoogleLogin}
//           disabled={submitting}
//         >
//           <span className="auth-google-icon">G</span>
//           Log in with Google
//         </button>

//         <div className="auth-divider">
//           <span />
//           <small>OR</small>
//           <span />
//         </div>

//         <form className="auth-form" onSubmit={handleSubmit}>
//           <label htmlFor="login-email">Email Address</label>

//           <div className="auth-input-wrap">
//             <Mail size={16} />

//             <input
//               id="login-email"
//               type="email"
//               placeholder="Enter your email address"
//               autoComplete="email"
//               value={email}
//               onChange={(event) => setEmail(event.target.value)}
//               required
//             />
//           </div>

//           <label htmlFor="login-password">Password</label>

//           <div className="auth-input-wrap">
//             <LockKeyhole size={16} />

//             <input
//               id="login-password"
//               type={showPassword ? "text" : "password"}
//               placeholder="Enter your password"
//               autoComplete="current-password"
//               value={password}
//               onChange={(event) => setPassword(event.target.value)}
//               required
//             />

//             <button
//               type="button"
//               className="auth-password-toggle"
//               onClick={() => setShowPassword((visible) => !visible)}
//               aria-label={showPassword ? "Hide password" : "Show password"}
//             >
//               {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
//             </button>
//           </div>

//           <div className="auth-options">
//             <label className="auth-checkbox-label">
//               <input
//                 type="checkbox"
//                 checked={rememberMe}
//                 onChange={(event) => setRememberMe(event.target.checked)}
//               />
//               <span>Remember me</span>
//             </label>

//             <button
//               type="button"
//               className="auth-text-button"
//               onClick={() =>
//                 setError("Please contact your administrator to reset your password.")
//               }
//             >
//               Forgot password?
//             </button>
//           </div>

//           {error && (
//             <p className="auth-error" role="alert">
//               {error}
//             </p>
//           )}

//           <button
//             type="submit"
//             className="auth-primary-button"
//             disabled={submitting}
//           >
//             {submitting ? "Logging in..." : "Log in"}
//             <ArrowRight size={17} />
//           </button>
//         </form>

//         <p className="auth-switch">
//           Don&apos;t have an account?{" "}
//             <button
//               type="button"
//               onClick={() => {
//                 if (onSignup) {
//                   onSignup();
//                 } else {
//                   window.location.href = "/Signup";
//                 }
//               }}
//               className="auth-text-button"
//             >
//               Sign up
//             </button>
//         </p>

//         <div className="auth-security-note">
//           <ShieldCheck size={14} />
//           Your civic account is protected.
//         </div>
//       </section>
//     </main>
//   );
// }



import { useState } from "react";
import {
  ArrowRight,
  Eye,
  EyeOff,
  KeyRound,
  ShieldCheck,
} from "lucide-react";
import { DEMO_ACCOUNTS } from "../lib/demoAccounts";
import "./Auth.css";

export default function Login({ onLogin, onSignup }) {
  const [accountId, setAccountId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!accountId.trim() || !password) {
      setError("Enter your account ID and password.");
      return;
    }

    setSubmitting(true);

    try {
      if (typeof onLogin !== "function") {
        throw new Error("Login handler is not configured in App.jsx.");
      }

      // Preserve the original account-ID authentication contract.
      await onLogin(accountId.trim(), password, { rememberMe });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Login failed. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  function selectDemo(account) {
    setAccountId(account.id);
    setPassword(account.password);
    setError("");
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-heading">
          <div className="auth-brand-icon">
            <ShieldCheck size={23} />
          </div>

          <h1>Log in to Your Account</h1>
          <p>Continue to CityWatch AI</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="login-account-id">Account ID</label>

          <div className="auth-input-wrap">
            <KeyRound size={16} />

            <input
              id="login-account-id"
              name="accountId"
              type="text"
              placeholder="e.g. CW-CIT-1001"
              autoComplete="username"
              value={accountId}
              onChange={(event) => setAccountId(event.target.value)}
              required
            />
          </div>

          <label htmlFor="login-password">Password</label>

          <div className="auth-input-wrap">
            <KeyRound size={16} />

            <input
              id="login-password"
              name="password"
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />

            <button
              type="button"
              className="auth-password-toggle"
              onClick={() => setShowPassword((value) => !value)}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          <div className="auth-options">
            <label className="auth-checkbox-label">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(event) => setRememberMe(event.target.checked)}
              />
              <span>Remember me</span>
            </label>
          </div>

          {error && (
            <p className="auth-error" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="auth-primary-button"
            disabled={submitting}
          >
            {submitting ? "Logging in..." : "Log in"}
            <ArrowRight size={17} />
          </button>
        </form>

        <div className="auth-demo-section">
          <div className="auth-demo-heading">
            <span>DEMO ACCOUNTS</span>
            <span>Sample access</span>
          </div>

          {DEMO_ACCOUNTS.map((account) => (
            <button
              key={account.role}
              type="button"
              className="auth-demo-account"
              onClick={() => selectDemo(account)}
            >
              <span>
                <strong>{account.label}</strong>
                <small>{account.id}</small>
              </span>

              <span className="auth-demo-use">Use account</span>
            </button>
          ))}
        </div>

        <p className="auth-switch">
          Don&apos;t have an account?{" "}
          <button
            type="button"
            className="auth-text-button"
            onClick={() => {
              if (onSignup) {
                onSignup();
              } else {
                window.location.href = "/signup";
              }
            }}
          >
            Sign up
          </button>
        </p>

        <div className="auth-security-note">
          <ShieldCheck size={14} />
          CityWatch AI demo workspace
        </div>
      </section>
    </main>
  );
}
