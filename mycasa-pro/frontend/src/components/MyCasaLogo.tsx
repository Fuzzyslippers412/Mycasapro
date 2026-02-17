export function MyCasaLogo({ size = 24 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* House roof */}
      <path
        d="M12 2L3 9V11H5V21H19V11H21V9L12 2Z"
        fill="url(#gradient1)"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Door */}
      <path
        d="M9 21V14H15V21"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Window */}
      <circle
        cx="9"
        cy="12"
        r="1.5"
        fill="currentColor"
        opacity="0.8"
      />
      <circle
        cx="15"
        cy="12"
        r="1.5"
        fill="currentColor"
        opacity="0.8"
      />
      <defs>
        <linearGradient id="gradient1" x1="3" y1="2" x2="21" y2="21" gradientUnits="userSpaceOnUse">
          <stop stopColor="#6366f1" />
          <stop offset="1" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
    </svg>
  );
}
