import React, { useRef } from "react";
import styled, { keyframes } from "styled-components";
import { FaUpload } from "react-icons/fa";

const UploadBox = styled.div`
  border: 2px dashed #39ff14;
  background: #181818;
  color: #39ff14;
  padding: 2rem;
  margin: 2rem auto;
  width: 90%;
  max-width: 500px;
  text-align: center;
  border-radius: 10px;
  transition: border 0.2s;
  cursor: pointer;
  &:hover {
    border: 2px solid #ff1744;
    color: #ff1744;
  }
`;

const HiddenInput = styled.input`
  display: none;
`;

const ProgressBarContainer = styled.div`
  background: #222;
  border: 1.5px solid #39ff14;
  border-radius: 8px;
  margin: 1.5rem auto 0 auto;
  width: 100%;
  max-width: 400px;
  height: 28px;
  overflow: hidden;
  box-shadow: 0 0 8px #39ff1444;
`;

const flicker = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
`;

const ProgressBarFill = styled.div`
  height: 100%;
  background: linear-gradient(90deg, #39ff14 60%, #ff1744 100%);
  width: ${props => props.progress || 0}%;
  transition: width 0.3s;
  animation: ${flicker} 1.2s infinite alternate;
  box-shadow: 0 0 16px #39ff1499;
`;

const ProgressText = styled.div`
  color: #39ff14;
  font-family: 'Fira Mono', 'Consolas', monospace;
  font-size: 1.1rem;
  margin-top: 0.5rem;
  text-shadow: 0 0 4px #39ff1499;
  text-align: center;
  width: 100%;
  display: flex;
  justify-content: center;
`;

const UploadResult = styled.div`
  color: #ff1744;
  font-family: 'Fira Mono', 'Consolas', monospace;
  font-size: 1.1rem;
  margin-top: 1rem;
  text-align: center;
`;

export default function UploadArea({ onFileSelect, uploading, progress, uploadResult }) {
  const fileInput = useRef();

  const handleBoxClick = () => fileInput.current.click();

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0]);
    }
  };

  return (
    <>
      <UploadBox onClick={handleBoxClick}>
        <FaUpload style={{ fontSize: "2rem", marginBottom: "0.5rem" }} />
        <div>Click or drag a file here to upload</div>
        <HiddenInput
          type="file"
          ref={fileInput}
          onChange={handleFileChange}
          accept=".txt,.json,.zip,.rar,.7z,.xlsx,.xls,.csv"
        />
      </UploadBox>
      {uploading && (
        <>
          <ProgressBarContainer>
            <ProgressBarFill progress={progress} />
          </ProgressBarContainer>
          <ProgressText>
            Uploading... {progress}%
          </ProgressText>
        </>
      )}
      {uploadResult && (
        <UploadResult>
          Upload done!<br />
          <span style={{ color: '#39ff14' }}>{uploadResult.inserted_rows}</span> rows added.<br />
          {uploadResult.json_file && (
            <a href={uploadResult.json_file} target="_blank" rel="noopener noreferrer" style={{ color: '#39ff14', textDecoration: 'underline' }}>
              Download parsed JSON
            </a>
          )}
        </UploadResult>
      )}
    </>
  );
} 