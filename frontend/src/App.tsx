import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import MapPage from './pages/MapPage'
import TaskPage from './pages/TaskPage'
import ProfilePage from './pages/ProfilePage'
import ClassesPage from './pages/ClassesPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<MapPage />} />
          <Route path="/task/:id" element={<TaskPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/classes" element={<ClassesPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
