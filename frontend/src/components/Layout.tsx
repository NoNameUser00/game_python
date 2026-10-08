import { NavLink, Outlet } from 'react-router-dom'
import { APP_NAME } from '../constants'
import { useAuth } from '../auth'

/** Шапка приложения + место для контента страниц. */
export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <header className="app-header">
        <NavLink to="/" className="brand">
          <span className="brand-logo">🐍</span>
          <span className="brand-name">{APP_NAME}</span>
        </NavLink>

        <nav className="app-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            🗺️ Карта
          </NavLink>
          <NavLink to="/profile" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            👤 Профиль
          </NavLink>
          {user?.role === 'teacher' && (
            <NavLink to="/classes" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              🏫 Классы
            </NavLink>
          )}
        </nav>

        <div className="header-right">
          {user && (
            <span className="level-badge" title={`${user.xp} XP`}>
              ⭐ Уровень {user.level}
            </span>
          )}
          <button type="button" className="btn btn-ghost" onClick={logout}>
            Выйти
          </button>
        </div>
      </header>

      <main className="app-content">
        <Outlet />
      </main>
    </div>
  )
}
