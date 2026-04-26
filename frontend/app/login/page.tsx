'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email || !password || (mode === 'signup' && !name)) {
      setError('Please fill in all fields.');
      return;
    }
    setLoading(true);
    // Simulate auth — swap out for real Supabase auth call
    await new Promise(r => setTimeout(r, 1200));
    setLoading(false);
    router.push('/dashboard');
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');
        *{box-sizing:border-box;margin:0;padding:0;-webkit-font-smoothing:antialiased}
        :root{
          --bg:#060810;--s1:#090E1A;--s2:#0D1322;--s3:#12192E;
          --blue:#00C8F5;--gold:#C9991E;--green:#00D97E;--red:#F04438;
          --ink:#DCE5F8;--ink2:#60789E;--ink3:#2E4266;
          --border:rgba(255,255,255,.07);--border-a:rgba(0,200,245,.32);
          --r1:6px;--r2:10px;--r3:14px;--r4:22px;
          --f:'Inter',system-ui,sans-serif;--mono:'JetBrains Mono',monospace;
        }
        html,body{background:var(--bg);color:var(--ink);font-family:var(--f);font-size:13px;line-height:1.5;min-height:100vh;}

        /* Background layers */
        .login-bg{
          position:fixed;inset:0;z-index:0;overflow:hidden;
          background:var(--bg);
        }
        .login-bg::before{
          content:'';position:absolute;inset:0;
          background:
            radial-gradient(ellipse 70% 55% at 15% 40%, rgba(0,200,245,.07) 0%, transparent 65%),
            radial-gradient(ellipse 50% 40% at 85% 60%, rgba(201,153,30,.05) 0%, transparent 60%),
            radial-gradient(ellipse 40% 35% at 50% 0%, rgba(0,200,245,.04) 0%, transparent 55%);
        }
        .login-bg::after{
          content:'';position:absolute;inset:0;opacity:.018;
          background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23n)'/%3E%3C/svg%3E");
          background-repeat:repeat;background-size:180px 180px;pointer-events:none;
        }

        /* Grid lines */
        .grid-lines{
          position:fixed;inset:0;z-index:0;pointer-events:none;
          background-image:
            linear-gradient(rgba(0,200,245,.014) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,200,245,.014) 1px, transparent 1px);
          background-size:48px 48px;
        }

        /* Layout */
        .login-root{position:relative;z-index:1;display:flex;min-height:100vh;}

        /* Left panel */
        .login-left{
          flex:0 0 480px;display:flex;flex-direction:column;justify-content:space-between;
          padding:52px;border-right:1px solid var(--border);
          background:linear-gradient(180deg, rgba(6,8,16,.9) 0%, rgba(9,14,26,.95) 100%);
          backdrop-filter:blur(12px);
        }
        .brand{display:flex;align-items:center;gap:10px;}
        .brand-icon{width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,rgba(0,200,245,.2),rgba(0,200,245,.05));border:1px solid rgba(0,200,245,.25);display:flex;align-items:center;justify-content:center;font-size:14px;color:var(--blue);}
        .brand-name{font-size:17px;font-weight:800;color:var(--ink);letter-spacing:-.5px;}
        .brand-name span{color:var(--blue);}

        .left-hero{flex:1;display:flex;flex-direction:column;justify-content:center;padding:48px 0;}
        .left-eyebrow{display:inline-flex;align-items:center;gap:7px;font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--blue);margin-bottom:24px;}
        .eyebrow-dot{width:5px;height:5px;border-radius:50%;background:var(--blue);box-shadow:0 0 6px rgba(0,200,245,.6);animation:pulse 2s infinite;}
        @keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(0,200,245,.5)}50%{opacity:.6;box-shadow:0 0 0 5px rgba(0,200,245,0)}}
        .left-h1{font-size:38px;font-weight:800;line-height:1.1;letter-spacing:-1.2px;color:var(--ink);margin-bottom:18px;}
        .left-h1 .b{background:linear-gradient(135deg,var(--blue),rgba(0,200,245,.65));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
        .left-h1 .g{background:linear-gradient(135deg,var(--gold),rgba(201,153,30,.65));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
        .left-p{font-size:13px;color:var(--ink2);line-height:1.75;max-width:320px;}

        .left-stats{display:flex;flex-direction:column;gap:10px;margin-top:36px;}
        .stat-item{display:flex;align-items:center;gap:12px;padding:12px 16px;background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:var(--r2);}
        .stat-item-icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;}
        .stat-item-val{font-size:15px;font-weight:800;font-family:var(--mono);color:var(--ink);letter-spacing:-.5px;}
        .stat-item-lbl{font-size:10px;color:var(--ink3);margin-top:1px;}

        .left-footer{font-size:9px;color:var(--ink3);line-height:1.6;}

        /* Right panel – form */
        .login-right{
          flex:1;display:flex;align-items:center;justify-content:center;
          padding:48px 32px;
        }
        .login-card{
          width:100%;max-width:400px;
        }

        .tab-row{display:flex;background:var(--s1);border:1px solid var(--border);border-radius:var(--r3);padding:4px;margin-bottom:28px;}
        .tab{flex:1;text-align:center;padding:9px 0;font-size:12px;font-weight:600;border-radius:var(--r2);cursor:pointer;transition:all .15s;color:var(--ink3);border:none;background:transparent;font-family:var(--f);}
        .tab.active{background:var(--blue);color:#000;box-shadow:0 0 12px rgba(0,200,245,.3);}

        .form-heading{font-size:22px;font-weight:800;color:var(--ink);letter-spacing:-.5px;margin-bottom:6px;}
        .form-sub{font-size:12px;color:var(--ink2);margin-bottom:28px;line-height:1.6;}

        .inp-group{margin-bottom:14px;}
        .inp-label{font-size:8.5px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:7px;display:block;}
        .inp{
          width:100%;background:var(--s1);border:1px solid var(--border);border-radius:var(--r2);
          padding:12px 15px;color:var(--ink);font-family:var(--f);font-size:13px;
          outline:none;transition:border-color .15s,box-shadow .15s;
        }
        .inp:focus{border-color:var(--border-a);box-shadow:0 0 0 3px rgba(0,200,245,.07);}
        .inp::placeholder{color:var(--ink3);}

        .divider{display:flex;align-items:center;gap:12px;margin:18px 0;}
        .divider hr{flex:1;border:none;border-top:1px solid var(--border);}
        .divider span{font-size:10px;color:var(--ink3);}

        .btn-submit{
          width:100%;padding:13px;background:var(--blue);color:#000;border:none;
          border-radius:var(--r2);font-family:var(--f);font-size:13px;font-weight:700;
          cursor:pointer;letter-spacing:.02em;
          box-shadow:0 0 20px rgba(0,200,245,.25);
          transition:box-shadow .15s,transform .12s,opacity .15s;
          position:relative;overflow:hidden;
        }
        .btn-submit:hover:not(:disabled){box-shadow:0 0 32px rgba(0,200,245,.45);transform:translateY(-1px);}
        .btn-submit:disabled{opacity:.6;cursor:wait;}
        .btn-submit::before{
          content:'';position:absolute;top:0;left:-100%;width:60%;height:100%;
          background:linear-gradient(90deg,transparent,rgba(255,255,255,.15),transparent);
          transform:skewX(-20deg);animation:shimmer 2.2s infinite;
        }
        @keyframes shimmer{0%{left:-100%}100%{left:160%}}

        .btn-google{
          width:100%;padding:12px;background:transparent;color:var(--ink);
          border:1px solid var(--border);border-radius:var(--r2);
          font-family:var(--f);font-size:12.5px;font-weight:500;cursor:pointer;
          display:flex;align-items:center;justify-content:center;gap:10px;
          transition:border-color .15s,background .15s;
        }
        .btn-google:hover{border-color:rgba(255,255,255,.14);background:rgba(255,255,255,.03);}

        .error-box{
          background:rgba(240,68,56,.07);border:1px solid rgba(240,68,56,.18);
          border-radius:var(--r2);padding:10px 14px;font-size:11px;color:var(--red);
          margin-bottom:14px;line-height:1.5;
        }

        .terms{font-size:9.5px;color:var(--ink3);text-align:center;margin-top:14px;line-height:1.6;}
        .terms a{color:var(--blue);cursor:pointer;}

        .back-link{
          display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--ink2);
          margin-top:24px;cursor:pointer;transition:color .15s;text-decoration:none;
        }
        .back-link:hover{color:var(--ink);}

        .loading-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;animation:blink 1s infinite;}
        .loading-dot:nth-child(2){animation-delay:.2s;}
        .loading-dot:nth-child(3){animation-delay:.4s;}
        @keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}
      `}</style>

      <div className="login-bg" />
      <div className="grid-lines" />

      <div className="login-root">
        {/* Left: branding + stats */}
        <div className="login-left">
          <div className="brand">
            <div className="brand-icon">◈</div>
            <div className="brand-name">Stock<span>Sense</span></div>
          </div>

          <div className="left-hero">
            <div className="left-eyebrow">
              <div className="eyebrow-dot" />
              India's Geopolitical Intelligence Platform
            </div>
            <h1 className="left-h1">
              Institutional<br />
              grade analysis,<br />
              <span className="b">built for</span> <span className="g">India.</span>
            </h1>
            <p className="left-p">
              PE ratios, ROE signals, IPO scoring, and geopolitical risk maps — all calibrated to Indian markets and your investment profile.
            </p>

            <div className="left-stats">
              {[
                { icon: '📈', val: '2,847', lbl: 'NSE + BSE Stocks Tracked', bg: 'rgba(0,200,245,.08)', bc: 'rgba(0,200,245,.15)' },
                { icon: '⚡', val: '<2s', lbl: 'RHP / DRHP Analysis Speed', bg: 'rgba(0,217,126,.07)', bc: 'rgba(0,217,126,.14)' },
                { icon: '🌐', val: '14', lbl: 'Geopolitical Event Sources', bg: 'rgba(201,153,30,.08)', bc: 'rgba(201,153,30,.15)' },
              ].map(s => (
                <div key={s.lbl} className="stat-item">
                  <div className="stat-item-icon" style={{ background: s.bg, border: `1px solid ${s.bc}` }}>{s.icon}</div>
                  <div>
                    <div className="stat-item-val">{s.val}</div>
                    <div className="stat-item-lbl">{s.lbl}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="left-footer">
            StockSense is not SEBI-registered. Analysis is educational only.<br />
            © 2026 StockSense India · Privacy · Terms
          </div>
        </div>

        {/* Right: auth form */}
        <div className="login-right">
          <div className="login-card">
            {/* Tab switcher */}
            <div className="tab-row">
              <button className={`tab${mode === 'login' ? ' active' : ''}`} onClick={() => { setMode('login'); setError(''); }}>Sign In</button>
              <button className={`tab${mode === 'signup' ? ' active' : ''}`} onClick={() => { setMode('signup'); setError(''); }}>Create Account</button>
            </div>

            <div className="form-heading">
              {mode === 'login' ? 'Welcome back' : 'Start for free'}
            </div>
            <div className="form-sub">
              {mode === 'login'
                ? 'Sign in to your StockSense account to continue.'
                : 'Create your account and access institutional-grade analysis.'}
            </div>

            {/* Google OAuth */}
            <button className="btn-google" type="button">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              Continue with Google
            </button>

            <div className="divider">
              <hr /><span>or</span><hr />
            </div>

            <form onSubmit={handleSubmit}>
              {error && <div className="error-box">{error}</div>}

              {mode === 'signup' && (
                <div className="inp-group">
                  <label className="inp-label">Full Name</label>
                  <input className="inp" type="text" placeholder="Vikram Sharma" value={name} onChange={e => setName(e.target.value)} />
                </div>
              )}

              <div className="inp-group">
                <label className="inp-label">Email Address</label>
                <input className="inp" type="email" placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} />
              </div>

              <div className="inp-group" style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 }}>
                  <label className="inp-label" style={{ margin: 0 }}>Password</label>
                  {mode === 'login' && <a style={{ fontSize: 10, color: 'var(--blue)', cursor: 'pointer' }}>Forgot password?</a>}
                </div>
                <input className="inp" type="password" placeholder="••••••••••" value={password} onChange={e => setPassword(e.target.value)} />
              </div>

              <button className="btn-submit" type="submit" disabled={loading}>
                {loading ? (
                  <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
                    <span className="loading-dot" />
                    <span className="loading-dot" />
                    <span className="loading-dot" />
                  </span>
                ) : (
                  mode === 'login' ? 'Sign In →' : 'Create Account →'
                )}
              </button>

              <p className="terms">
                {mode === 'signup'
                  ? <>By creating an account you agree to our <a>Terms of Service</a> and <a>Privacy Policy</a>.</>
                  : <>Don't have an account? <a onClick={() => { setMode('signup'); setError(''); }}>Sign up free</a></>
                }
              </p>
            </form>

            <a className="back-link" onClick={() => window.history.back()}>
              ← Back to StockSense
            </a>
          </div>
        </div>
      </div>
    </>
  );
}
