import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
// Шрифты локально (npm) — работают офлайн, без google-шлюза
import '@fontsource/caveat/400.css'
import '@fontsource/caveat/700.css'
import '@fontsource/onest/400.css'
import '@fontsource/onest/700.css'
import '@fontsource/onest/800.css'
import '@fontsource/fira-code/400.css'
import '@fontsource/fira-code/700.css'
import './styles.css'
import App from './App.tsx'
import { AuthProvider } from './auth'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
