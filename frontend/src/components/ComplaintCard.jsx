export default function ComplaintCard({ title = 'Complaint', status = 'Open' }) {
  return (
    <div style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: '1rem' }}>
      <h3>{title}</h3>
      <p>Status: {status}</p>
    </div>
  );
}
