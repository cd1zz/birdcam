/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  safelist: [
    // Ensure common UI classes are always included
    'bg-white', 'bg-gray-50', 'bg-gray-100', 'bg-gray-200', 'bg-gray-900',
    'bg-blue-50', 'bg-blue-600', 'bg-blue-700', 'bg-green-50', 'bg-green-600',
    'bg-red-50', 'bg-red-200', 'bg-yellow-50', 'bg-orange-50', 'bg-purple-50',
    'text-white', 'text-gray-400', 'text-gray-500', 'text-gray-600', 'text-gray-700', 'text-gray-800', 'text-gray-900',
    'text-blue-600', 'text-green-600', 'text-red-400', 'text-red-800', 'text-yellow-800',
    'shadow-sm', 'shadow-md', 'shadow-lg', 'rounded', 'rounded-lg', 'rounded-full',
    'border', 'border-gray-300', 'border-blue-600', 'border-red-200', 'border-yellow-200',
    // Dark mode classes
    'dark:bg-gray-800', 'dark:bg-gray-900', 'dark:bg-gray-700', 'dark:bg-gray-600',
    'dark:text-white', 'dark:text-gray-300', 'dark:text-gray-200', 'dark:text-gray-100',
    'dark:border-gray-600', 'dark:border-gray-700', 'dark:hover:bg-gray-700'
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}