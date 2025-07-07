import React from "react";
import styled, { keyframes } from "styled-components";
import { FaExclamationTriangle } from "react-icons/fa";

const flicker = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
`;

const Banner = styled.div`
  background: #2a0000;
  color: #ff1744;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  padding: 0.75rem 0;
  font-family: 'Fira Mono', 'Consolas', monospace;
  letter-spacing: 1px;
  animation: ${flicker} 1.2s infinite alternate;
  border-bottom: 2px solid #ff1744;
`;

const Icon = styled(FaExclamationTriangle)`
  margin-right: 0.75rem;
  font-size: 1.5rem;
`;

export default function DangerBanner() {
  return (
    <Banner>
      <Icon />
      WARNING: Leaked credentials detected! Use at your own risk.
    </Banner>
  );
} 