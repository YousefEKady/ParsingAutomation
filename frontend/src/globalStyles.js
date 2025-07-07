import { createGlobalStyle } from "styled-components";

const GlobalStyle = createGlobalStyle`
  body {
    background: #111;
    color: #39ff14;
    font-family: 'Fira Mono', 'Consolas', monospace;
    margin: 0;
    padding: 0;
    min-height: 100vh;
    letter-spacing: 0.5px;
    overflow-x: hidden;
  }
  ::selection {
    background: #39ff14;
    color: #111;
  }
  a {
    color: #39ff14;
    text-decoration: none;
  }
`;

export default GlobalStyle; 