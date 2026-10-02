export default function FileUpload({ label, file, onChange, accept = ".pdf,.docx" }) {
  return (
    <div className="form-group">
      <label className="form-label">{label}</label>
      <div className="file-upload">
        <input type="file" accept={accept} onChange={(e) => onChange(e.target.files[0])} />
        {file && <p className="file-upload-filename">Selected: {file.name}</p>}
      </div>
    </div>
  );
}