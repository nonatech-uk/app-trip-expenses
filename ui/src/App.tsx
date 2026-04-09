import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Shell from './components/layout/Shell'
import TripsPage from './pages/TripsPage'
import TripPage from './pages/TripPage'
import SharePage from './pages/SharePage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public share page — no Shell */}
        <Route path="/share/:slug/:memberId" element={<SharePage />} />

        {/* Authenticated routes with Shell */}
        <Route element={<Shell />}>
          <Route path="/" element={<TripsPage />} />
          <Route path="/trip/:slug" element={<TripPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
