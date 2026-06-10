import React from 'react';
import { Sidebar } from './Sidebar';
import './Layout.css';

export const Layout = ({ children }) => {
  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="topnav">
          <div className="topnav-spacer" aria-hidden="true"></div>
        </header>
        <div className="page-content">
          {children}
        </div>
      </main>
    </div>
  );
};
