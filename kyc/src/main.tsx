import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import Ui from './Ui.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Ui />
  </StrictMode>,
)
