"""Small-signal model of the G70 steering loop with the plant identified from logs (stiffness k, damping c, delay d)
and the V1 torque controller's law. Compared against what sway.py measured, then used to rank candidate settings."""
import numpy as np
BANDS=[(0.10,0.20),(0.20,0.30),(0.30,0.45),(0.45,0.70),(0.70,1.00),(1.00,1.60)]
fc=np.array([(a+b)/2 for a,b in BANDS]); s=2j*np.pi*fc
def kp_at(v): return float(np.interp(v,[1,1.5,2.0,3.0,5,7.5,10,15,30],[250,120,65,30,11.5,5.5,3.5,2.0,0.8]))
def plant(k,c,d): return np.exp(-s*d)/(k+c*s)                 # m/s2 per count
def T(P,G,fr,thr,Dc,v,ki=0.15,kpscale=1.0,jff=0.0,jlp=0.0,centre=1.0,kj=0.3):
    """actual / request. G counts per m/s2 beyond the knee; centre = curve's centre gain (small-signal slope near zero);
    jff = feed-forward on the request's rate, seconds (torque = G*(r + jff*dr/dt)), low-passed with jlp seconds"""
    g=G*centre; sf=fr/thr; kp=kp_at(v)*kpscale; C=kp+ki/s+sf; lp=1/(1+s/(2*np.pi*1.2))
    lead=jff*s/(1+s*jlp) if jff else 0
    num=1+lead+C*np.exp(-s*Dc)+kj*sf*s*lp*np.exp(-s*(Dc-0.19))
    return P*g*num/(1+P*g*C)
def show(name,H): print(f"{name:44s} "+"  ".join(f"{abs(h):.2f}/{-np.degrees(np.angle(h)):4.0f}" for h in H))
if __name__=="__main__":
    v=33.0
    print("bands Hz: "+"  ".join(f"{a:.2f}-{b:.2f}" for a,b in BANDS)+"   (gain / lag deg)")
    meas_e1=[(0.84,19),(0.90,81),(0.89,92),(0.82,109),(0.42,130),(0.28,109)]
    meas_15=[(1.01,30),(1.29,53),(1.45,74),(1.20,81),(0.78,78),(0.38,94)]
    meas_16=[(0.84,48),(1.10,70),(1.21,89),(0.99,99),(0.39,113),(0.21,133)]
    print("ours e1 measured                             "+"  ".join(f"{g:.2f}/{l:4d}" for g,l in meas_e1))
    for k,c,d in ((48,24,0.20),(52,26,0.20),(60,26,0.22),(80,28,0.24)):
        show(f"  model k={k} c={c} d={d}",T(plant(k,c,d),384/4.5,0.07,0.40,0.20,v))
    print("his 2.5 v1 delay .33 measured                "+"  ".join(f"{g:.2f}/{l:4d}" for g,l in meas_15))
    for k,c,d in ((48,24,0.20),(52,26,0.20),(60,26,0.22),(80,28,0.24)):
        show(f"  model k={k} c={c} d={d}",T(plant(k,c,d),270/2.5,0.055,0.20,0.33,v))
    print("his 3.1 v1 delay .33 measured                "+"  ".join(f"{g:.2f}/{l:4d}" for g,l in meas_16))
    for k,c,d in ((48,24,0.20),(52,26,0.20),(60,26,0.22),(80,28,0.24)):
        show(f"  model k={k} c={c} d={d}",T(plant(k,c,d),270/3.1,0.055,0.20,0.33,v))
