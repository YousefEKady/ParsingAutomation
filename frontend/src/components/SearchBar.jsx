import React, { useState } from "react";
import styled, { keyframes } from "styled-components";
import { FaSearch } from "react-icons/fa";

const blink = keyframes`
  0%, 100% { border-right: 2px solid #39ff14; }
  50% { border-right: 2px solid transparent; }
`;

const Bar = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 2rem 0 1rem 0;
`;

const Input = styled.input`
  background: #181818;
  color: #39ff14;
  border: none;
  border-bottom: 2px solid #39ff14;
  font-size: 1.2rem;
  font-family: 'Fira Mono', 'Consolas', monospace;
  padding: 0.5rem 1rem;
  width: 350px;
  outline: none;
  animation: ${blink} 1s step-end infinite;
  margin-right: 0.5rem;
`;

const Icon = styled(FaSearch)`
  font-size: 1.3rem;
`;

export default function SearchBar({ onSearch }) {
  const [query, setQuery] = useState("");

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <Bar>
      <Input
        placeholder="Search leaks..."
        value={query}
        onChange={e => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <Icon />
    </Bar>
  );
} 