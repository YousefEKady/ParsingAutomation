import React, { useState } from "react";
import GlobalStyle from "./globalStyles";
import Header from "./components/Header";
import UploadArea from "./components/UploadArea";
import SearchBar from "./components/SearchBar";
import ResultsTable from "./components/ResultsTable";
import StatusPanel from "./components/StatusPanel";
import DangerBanner from "./components/DangerBanner";
import axios from "axios";

function App() {
  const [results, setResults] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState(null);

  const handleFileSelect = async (file) => {
    setUploading(true);
    setProgress(0);
    setUploadResult(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await axios.post("/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          if (e.total) {
            setProgress(Math.round((e.loaded * 100) / e.total));
          }
        },
      });
      setResults(res.data.details || []);
      setUploadResult({
        inserted_rows: res.data.inserted_rows,
        json_file: res.data.json_file,
      });
    } catch (e) {
      alert("Upload failed: " + (e.response?.data?.detail || e.message));
    }
    setUploading(false);
    setProgress(0);
  };

  const handleSearch = async (query) => {
    try {
      const res = await axios.post("/search", { query });
      setResults(res.data.results || []);
    } catch (e) {
      alert("Search failed: " + (e.response?.data?.detail || e.message));
    }
  };

  return (
    <>
      <GlobalStyle />
      <Header />
      <DangerBanner />
      <UploadArea
        onFileSelect={handleFileSelect}
        uploading={uploading}
        progress={progress}
        uploadResult={uploadResult}
      />
      <SearchBar onSearch={handleSearch} />
      <StatusPanel />
      <ResultsTable results={results} />
    </>
  );
}

export default App;
