import { Shell as SharedShell } from '@mees/shared-ui'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function Shell() {
  return (
    <SharedShell appName="Trips" sidebar={Sidebar}>
      <Outlet />
    </SharedShell>
  )
}
