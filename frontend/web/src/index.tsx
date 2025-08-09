import { createRoot } from 'react-dom/client';
import Landing from './pages/Landing';

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<Landing />);
}
