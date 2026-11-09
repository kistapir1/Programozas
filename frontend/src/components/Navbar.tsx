interface NavbarProps {
  onAuthClick?: () => void;
}

function Navbar({ onAuthClick }: NavbarProps) {
  return (
    <nav className="top-navbar">
      <span className="nav-brand">Menetrend kereső</span>
      <span className="nav-link auth-link" onClick={onAuthClick}>
        Belépés/Regisztráció
      </span>
    </nav>
  );
}

export default Navbar;