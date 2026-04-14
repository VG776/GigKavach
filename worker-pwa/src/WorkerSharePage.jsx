import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getWorkerProfileByToken, updateWorkerProfileByToken } from './api';

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
        async function loadProfile() {
            try {
                setError('');
                setNotice('');
                const data = await getWorkerProfileByToken(token);
                setProfile(data);
                setForm({
                    gig_platform: data.platform || 'Zomato',
                    shift: data.shift || 'Flexible',
                    gig_score: Number(data.gig_score || 50),
                    portfolio_score: Number(data.portfolio_score || 50),
                });
            } catch (err) {
                setError(err.message || 'Unable to load profile');
            }
        }

        if (token) loadProfile();
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

                {profile && (
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
