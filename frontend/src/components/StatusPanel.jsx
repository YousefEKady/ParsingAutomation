import React, { useEffect, useState } from "react";
import styled from "styled-components";
import { FaRobot } from "react-icons/fa";
import axios from "axios";

const Panel = styled.div`
  background: #181818;
  color: #39ff14;
  border: 1.5px solid #39ff14;
  border-radius: 8px;
  padding: 1rem 2rem;
  margin: 2rem auto 1rem auto;
  max-width: 500px;
  font-family: 'Fira Mono', 'Consolas', monospace;
  font-size: 1rem;
`;

const Row = styled.div`
  margin-bottom: 0.5rem;
`;

export default function StatusPanel() {
  const [status, setStatus] = useState({});

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await axios.get("/worker-status");
        setStatus(res.data);
      } catch {
        setStatus({ error: "Unable to fetch status" });
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Panel>
      <Row><FaRobot /> Telegram Worker Status</Row>
      <Row>Running: {String(status.running)}</Row>
      <Row>Last Checked: {status.last_checked || "-"}</Row>
      <Row>Last File: {status.last_file || "-"}</Row>
      <Row>Inserted Leaks: {status.inserted_leaks || 0}</Row>
      {status.errors && status.errors.length > 0 && (
        <Row style={{ color: '#ff1744' }}>Errors: {status.errors.join(", ")}</Row>
      )}
    </Panel>
  );
} 