import React from "react";
import styled, { keyframes } from "styled-components";

const glitch = keyframes`
  0% { text-shadow: 2px 0 red, -2px 0 blue; }
  20% { text-shadow: -2px 0 red, 2px 0 blue; }
  40% { text-shadow: 2px 0 red, -2px 0 blue; }
  60% { text-shadow: -2px 0 red, 2px 0 blue; }
  80% { text-shadow: 2px 0 red, -2px 0 blue; }
  100% { text-shadow: 2px 0 red, -2px 0 blue; }
`;

const HeaderBar = styled.header`
  background: #181818;
  padding: 2rem 0 1rem 0;
  text-align: center;
`;

const Title = styled.h1`
  color: #39ff14;
  font-size: 2.5rem;
  letter-spacing: 2px;
  font-family: 'Fira Mono', 'Consolas', monospace;
  animation: ${glitch} 1.5s infinite linear alternate-reverse;
  user-select: none;
`;

export default function Header() {
  return (
    <HeaderBar>
      <Title>LEAKED DB</Title>
    </HeaderBar>
  );
} 