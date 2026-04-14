import { Navigate, Route, Routes } from 'react-router-dom';
import { WorkerSharePage } from './WorkerSharePage';

export default function App() {
    return (
        <Routes>
            <Route path="/share/worker/:token" element={<WorkerSharePage />} />
            <Route path="*" element={<Navigate to="/share/worker/invalid" replace />} />
        </Routes>
    );
}
