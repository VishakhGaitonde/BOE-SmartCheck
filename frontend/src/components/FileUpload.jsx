export default function FileUpload({ label, file, onChange, accept = ".pdf,.docx", multiple = false }) {
  const list = multiple ? file || [] : file ? [file] : [];

  const handlePick = (e) => {
    const picked = Array.from(e.target.files);
    if (multiple) {
      onChange([...(file || []), ...picked]);
      e.target.value = "";
    } else {
      onChange(picked[0]);
    }
  };

  const remove = (index) => onChange(list.filter((_, i) => i !== index));

  return (
    <div className="form-group">
      <label className="form-label">{label}</label>
      <div className="file-upload">
        <input type="file" accept={accept} multiple={multiple} onChange={handlePick} />
        {list.map((f, i) => (
          <p key={i} className="file-upload-filename">
            {multiple ? f.name : `Selected: ${f.name}`}
            {multiple && (
              <button type="button" className="file-remove" onClick={() => remove(i)}>
                remove
              </button>
            )}
          </p>
        ))}
      </div>
    </div>
  );
}