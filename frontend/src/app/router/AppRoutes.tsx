import { Link, Route, Routes } from 'react-router'

import { ProjectCreatePage } from '../../pages/project-create'
import { ProjectsPage } from '../../pages/projects'
import { ProjectSettingsPage } from '../../pages/project-settings'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<ProjectsPage />} />
      <Route path="/projects/new" element={<ProjectCreatePage />} />
      <Route path="/projects/:projectId/settings" element={<ProjectSettingsPage />} />

      <Route
        path="*"
        element={
          <section>
            <h1>Страница не найдена</h1>
            <Link to="/">Вернуться к проектам</Link>
          </section>
        }
      />
    </Routes>
  )
}