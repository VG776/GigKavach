import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getWorkerProfileByToken, sessionLoginByToken, updateWorkerProfileByToken } from './api';

const SHIFTS = ['Flexible', 'Morning', 'Evening', 'Night'];
const PLATFORMS = ['Zomato', 'Swiggy'];

function derivePlanRecommendation(gigScore, portfolioScore) {
    if (gigScore >= 80 && portfolioScore >= 70) return 'Shield Pro';
    if (gigScore >= 70 && portfolioScore >= 50) return 'Shield Plus';
    return 'Shield Basic';
}

export function WorkerSharePage() {
    const { token } = useParams();
    const [profile, setProfile] = useState(null);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [notice, setNotice] = useState('');
    const [installEvent, setInstallEvent] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [authForm, setAuthForm] = useState({
        phone: '',
        password: '',
        digilocker_id: '',
    });

    const [form, setForm] = useState({
        gig_platform: 'Zomato',
        shift: 'Flexible',
        gig_score: 50,
        portfolio_score: 50,
    });

    useEffect(() => {
        const onBeforeInstallPrompt = (event) => {
            event.preventDefault();
            setInstallEvent(event);
        };

        window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt);
        return () => window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt);
    }, []);

    useEffect(() => {
        async function loadPreviewProfile() {
            try {
                const data = await getWorkerProfileByToken(token);
                setProfile(data);
                setAuthForm((prev) => ({ ...prev, phone: data.phone || '' }));
            } catch (err) {
                setError(err.message || 'Unable to load profile');
            }
        }

        if (token) loadPreviewProfile();
    }, [token]);

    const recommendation = useMemo(
        () => derivePlanRecommendation(Number(form.gig_score), Number(form.portfolio_score)),
        [form.gig_score, form.portfolio_score]
    );

    async function handleSave(event) {
        event.preventDefault();
        setSaving(true);
        setError('');
        setNotice('');

        try {
            const updates = {
                gig_platform: form.gig_platform,
                shift: form.shift,
                gig_score: Number(form.gig_score),
                portfolio_score: Number(form.portfolio_score),
            };
            const updated = await updateWorkerProfileByToken(token, updates);
            setProfile(updated.profile);
            setNotice('Profile preferences updated successfully.');
        } catch (err) {
            setError(err.message || 'Unable to save changes');
        } finally {
            setSaving(false);
        }
    }

    async function handleSessionLogin(event) {
        event.preventDefault();
        setSaving(true);
        setError('');
        setNotice('');

        try {
            const result = await sessionLoginByToken(token, authForm);
            const p = result.profile;
            setProfile(p);
            setForm({
                gig_platform: p.platform || 'Zomato',
                shift: p.shift || 'Flexible',
                gig_score: Number(p.gig_score || 50),
                portfolio_score: Number(p.portfolio_score || 50),
            });
            setIsAuthenticated(true);
            setNotice(result.demo_notice || 'Session login successful.');
        } catch (err) {
            setError(err.message || 'Unable to login');
        } finally {
            setSaving(false);
        }
    }

    async function handleInstall() {
        if (!installEvent) return;
        await installEvent.prompt();
        setInstallEvent(null);
    }

    return (
        <main className="page">
            <section className="card">
                <h1>GigKavach Worker</h1>
                <p className="sub">Your WhatsApp profile link</p>

                {installEvent && (
                    <button className="install" onClick={handleInstall}>
                        Install Shield App
                    </button>
                )}

                {error && <p className="error">{error}</p>}

                {!isAuthenticated && (
                    <form onSubmit={handleSessionLogin} className="form auth-form">
                        <div className="recommendation">
                            <p>Session login required</p>
                            <strong>Use phone + password + DigiLocker demo verification</strong>
                        </div>

                        <label>
                            Phone number
                            <input
                                type="tel"
                                value={authForm.phone}
                                onChange={(e) => setAuthForm((prev) => ({ ...prev, phone: e.target.value }))}
                                placeholder="9198xxxxxxx"
                                required
                            />
                        </label>

                        <label>
                            Password
                            <input
                                type="password"
                                value={authForm.password}
                                onChange={(e) => setAuthForm((prev) => ({ ...prev, password: e.target.value }))}
                                placeholder="Enter password"
                                required
                            />
                        </label>

                        <label>
                            DigiLocker ID (demo)
                            <input
                                type="text"
                                value={authForm.digilocker_id}
                                onChange={(e) => setAuthForm((prev) => ({ ...prev, digilocker_id: e.target.value }))}
                                placeholder="DLK-123456"
                                required
                            />
                        </label>

                        <p className="demo-note">
                            Demo note: DigiLocker verification is mocked. No DigiLocker data is stored.
                        </p>

                        <button type="submit" disabled={saving}>
                            {saving ? 'Logging in...' : 'Login to Start WhatsApp Session'}
                        </button>
                    </form>
                )}

                {profile && isAuthenticated && (
                    <>
                        <div className="grid">
                            <div>
                                <label>Name</label>
                                <p>{profile.name || 'Worker'}</p>
                            </div>
                            <div>
                                <label>Current Plan</label>
                                <p>{profile.plan || 'Shield Basic'}</p>
                            </div>
                            <div>
                                <label>Phone</label>
                                <p>{profile.phone || '-'}</p>
                            </div>
                            <div>
                                <label>UPI</label>
                                <p>{profile.upi_id || '-'}</p>
                            </div>
                        </div>

                        <form onSubmit={handleSave} className="form">
                            <label>
                                Platform
                                <select
                                    value={form.gig_platform}
                                    onChange={(e) => setForm((prev) => ({ ...prev, gig_platform: e.target.value }))}
                                >
                                    {PLATFORMS.map((p) => (
                                        <option value={p} key={p}>{p}</option>
                                    ))}
                                </select>
                            </label>

                            <label>
                                Shift
                                <select
                                    value={form.shift}
                                    onChange={(e) => setForm((prev) => ({ ...prev, shift: e.target.value }))}
                                >
                                    {SHIFTS.map((s) => (
                                        <option value={s} key={s}>{s}</option>
                                    ))}
                                </select>
                            </label>

                            <label>
                                Gig Score (0-100)
                                <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    value={form.gig_score}
                                    onChange={(e) => setForm((prev) => ({ ...prev, gig_score: e.target.value }))}
                                />
                            </label>

                            <label>
                                Portfolio Score (0-100)
                                <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    value={form.portfolio_score}
                                    onChange={(e) => setForm((prev) => ({ ...prev, portfolio_score: e.target.value }))}
                                />
                            </label>

                            <div className="recommendation">
                                <p>Recommended for you</p>
                                <strong>{recommendation}</strong>
                            </div>

                            <button type="submit" disabled={saving}>
                                {saving ? 'Saving...' : 'Save Preferences'}
                            </button>
                        </form>
                    </>
                )}

                {notice && <p className="notice">{notice}</p>}
            </section>
        </main>
    );
}
