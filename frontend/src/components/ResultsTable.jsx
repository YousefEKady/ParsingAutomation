import React from "react";
import styled from "styled-components";

const Table = styled.table`
  width: 95%;
  margin: 2rem auto;
  background: #181818;
  color: #39ff14;
  border-collapse: collapse;
  font-family: 'Fira Mono', 'Consolas', monospace;
  box-shadow: 0 0 10px #39ff1433;
`;

const Th = styled.th`
  background: #222;
  color: #ff1744;
  padding: 0.75rem 0.5rem;
  border-bottom: 2px solid #39ff14;
`;

const Td = styled.td`
  padding: 0.5rem;
  border-bottom: 1px solid #222;
  word-break: break-all;
`;

export default function ResultsTable({ results = [] }) {
  if (!results.length) return null;
  return (
    <Table>
      <thead>
        <tr>
          <Th>Software</Th>
          <Th>URL</Th>
          <Th>Username</Th>
          <Th>Password</Th>
          <Th>Date</Th>
        </tr>
      </thead>
      <tbody>
        {results.map((row, idx) => (
          <tr key={idx}>
            <Td>{row.software}</Td>
            <Td>{row.url}</Td>
            <Td>{row.username}</Td>
            <Td>{row.password}</Td>
            <Td>{row.date ? new Date(row.date).toLocaleString() : "-"}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
} 