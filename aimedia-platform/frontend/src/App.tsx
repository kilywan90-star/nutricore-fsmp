import { Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from './components/MainLayout'
import { ContentList } from './pages/ContentList'
import { ContentEditor } from './pages/ContentEditor'
import { ReviewList } from './pages/ReviewList'
import { PublishList } from './pages/PublishList'
import { DataDashboard } from './pages/DataDashboard'
import { Login } from './pages/Login'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Navigate to="/content" replace />} />
        <Route path="content" element={<ContentList />} />
        <Route path="content/new" element={<ContentEditor />} />
        <Route path="content/:id/edit" element={<ContentEditor />} />
        <Route path="review" element={<ReviewList />} />
        <Route path="publish" element={<PublishList />} />
        <Route path="dashboard" element={<DataDashboard />} />
      </Route>
    </Routes>
  )
}
