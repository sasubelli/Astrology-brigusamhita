package com.bhrigusamhita;

import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import java.util.Map;

/** BigDecimal port of the local orbital approximation. No binary floating point is used. */
final class PreciseAstronomy {
  private static final MathContext MC = new MathContext(34, RoundingMode.HALF_EVEN);
  private static final BigDecimal PI = new BigDecimal("3.141592653589793238462643383279503");
  private static final BigDecimal HALF_PI = PI.divide(new BigDecimal("2"), MC);
  private static final BigDecimal QUARTER_PI = PI.divide(new BigDecimal("4"), MC);
  private static final BigDecimal C360 = new BigDecimal("360"), C180 = new BigDecimal("180"), C90 = new BigDecimal("90");
  private static final BigDecimal D2R = PI.divide(C180, MC), R2D = C180.divide(PI, MC);
  private PreciseAstronomy() {}

  static BigDecimal ascendant(BigDecimal jd, BigDecimal latitude, BigDecimal longitude) {
    BigDecimal t=jd.subtract(new BigDecimal("2451545"),MC).divide(new BigDecimal("36525"),MC);
    BigDecimal gst=mod(new BigDecimal("280.46061837").add(new BigDecimal("360.98564736629").multiply(jd.subtract(new BigDecimal("2451545"),MC),MC),MC).add(new BigDecimal("0.000387933").multiply(t.multiply(t,MC),MC),MC).subtract(t.multiply(t,MC).multiply(t,MC).divide(new BigDecimal("38710000"),MC),MC),C360);
    BigDecimal eps=new BigDecimal("23.439291111").subtract(new BigDecimal("0.013004167").multiply(t,MC),MC).subtract(new BigDecimal("0.0000001639").multiply(t.multiply(t,MC),MC),MC).add(new BigDecimal("0.0000005036").multiply(t.multiply(t,MC).multiply(t,MC),MC),MC);
    BigDecimal lst=rad(mod(gst.add(longitude,MC),C360)), lat=rad(latitude), er=rad(eps);
    return mod(deg(atan2(cosRad(lst), sinRad(lst).negate().multiply(cosRad(er),MC).add(tanRad(lat).multiply(sinRad(er),MC),MC))),C360);
  }
  static BigDecimal longitude(String name, BigDecimal jd, BigDecimal ayanamsa) {
    BigDecimal d=jd.subtract(new BigDecimal("2451543.5"),MC); Sun sun=sun(d);
    BigDecimal tropical=switch(name) { case "Sun" -> sun.lon; case "Moon" -> moon(d,sun.lon,sun.mean); case "Mars", "Saturn" -> planet(name,d,sun); default -> null; };
    if(tropical==null) return null;
    return mod(tropical.subtract(ayanamsa,MC),C360);
  }
  private static Sun sun(BigDecimal d) { BigDecimal w=new BigDecimal("282.9404").add(new BigDecimal("0.0000470935").multiply(d,MC),MC), e=new BigDecimal("0.016709").subtract(new BigDecimal("0.000000001151").multiply(d,MC),MC), m=mod(new BigDecimal("356.0470").add(new BigDecimal("0.9856002585").multiply(d,MC),MC),C360), ea=kepler(m,e), xv=cos(ea).subtract(e,MC), yv=sqrt(BigDecimal.ONE.subtract(e.multiply(e,MC),MC)).multiply(sin(ea),MC), v=deg(atan2(yv,xv)), r=sqrt(xv.multiply(xv,MC).add(yv.multiply(yv,MC),MC)); return new Sun(mod(v.add(w,MC),C360),r,m,w); }
  private static BigDecimal planet(String name, BigDecimal d, Sun sun) { Orbit o=orbit(name,d); Vec v=xyz(o); BigDecimal xs=sun.r.multiply(cos(sun.lon),MC), ys=sun.r.multiply(sin(sun.lon),MC); return mod(deg(atan2(v.y.add(ys,MC),v.x.add(xs,MC))),C360); }
  private static BigDecimal moon(BigDecimal d,BigDecimal sunLon,BigDecimal sunM) { BigDecimal n=mod(new BigDecimal("125.1228").subtract(new BigDecimal("0.0529538083").multiply(d,MC),MC),C360), w=mod(new BigDecimal("318.0634").add(new BigDecimal("0.1643573223").multiply(d,MC),MC),C360), m=mod(new BigDecimal("115.3654").add(new BigDecimal("13.0649929509").multiply(d,MC),MC),C360); Orbit o=new Orbit(n,new BigDecimal("5.1454"),w,new BigDecimal("60.2666"),new BigDecimal("0.054900"),m); Vec v=xyz(o); BigDecimal lon=mod(deg(atan2(v.y,v.x)),C360), lm=mod(n.add(w,MC).add(m,MC),C360), dm=mod(lm.subtract(sunLon,MC),C360), f=mod(lm.subtract(n,MC),C360);
    lon=lon.add(sin(m.subtract(dm.multiply(new BigDecimal("2"),MC),MC)).multiply(new BigDecimal("-1.274"),MC),MC).add(sin(dm.multiply(new BigDecimal("2"),MC)).multiply(new BigDecimal("0.658"),MC),MC).add(sin(sunM).multiply(new BigDecimal("-0.186"),MC),MC).add(sin(m.multiply(new BigDecimal("2"),MC).subtract(dm.multiply(new BigDecimal("2"),MC),MC)).multiply(new BigDecimal("-0.059"),MC),MC).add(sin(m.subtract(dm.multiply(new BigDecimal("2"),MC),MC).add(sunM,MC)).multiply(new BigDecimal("-0.057"),MC),MC).add(sin(m.add(dm.multiply(new BigDecimal("2"),MC),MC)).multiply(new BigDecimal("0.053"),MC),MC).add(sin(dm.multiply(new BigDecimal("2"),MC).subtract(sunM,MC)).multiply(new BigDecimal("0.046"),MC),MC).add(sin(m.subtract(sunM,MC)).multiply(new BigDecimal("0.041"),MC),MC).add(sin(dm).multiply(new BigDecimal("-0.035"),MC),MC).add(sin(m.add(sunM,MC)).multiply(new BigDecimal("-0.031"),MC),MC).add(sin(f.multiply(new BigDecimal("2"),MC).subtract(dm.multiply(new BigDecimal("2"),MC),MC)).multiply(new BigDecimal("-0.015"),MC),MC).add(sin(m.subtract(dm.multiply(new BigDecimal("4"),MC),MC)).multiply(new BigDecimal("0.011"),MC),MC);
    return mod(lon,C360); }
  private static Orbit orbit(String name,BigDecimal d) { return switch(name) { case "Mars" -> new Orbit(add("49.5574","0.0000211081",d),add("1.8497","-0.0000000178",d),add("286.5016","0.0000292961",d),new BigDecimal("1.523688"),add("0.093405","0.000000002516",d),add("18.6021","0.5240207766",d)); case "Saturn" -> new Orbit(add("113.6634","0.0000238980",d),add("2.4886","-0.0000001081",d),add("339.3939","0.000029761",d),new BigDecimal("9.55475"),add("0.055546","-0.000000009499",d),add("316.9670","0.0334442282",d)); default -> throw new IllegalArgumentException("Unsupported precision planet"); }; }
  private static Vec xyz(Orbit o) { BigDecimal ea=kepler(o.m,o.e), xv=o.a.multiply(cos(ea).subtract(o.e,MC),MC), yv=o.a.multiply(sqrt(BigDecimal.ONE.subtract(o.e.multiply(o.e,MC),MC)),MC).multiply(sin(ea),MC), v=deg(atan2(yv,xv)), r=sqrt(xv.multiply(xv,MC).add(yv.multiply(yv,MC),MC)), vw=v.add(o.w,MC); return new Vec(r.multiply(cos(o.n).multiply(cos(vw),MC).subtract(sin(o.n).multiply(sin(vw),MC).multiply(cos(o.i),MC),MC),MC),r.multiply(sin(o.n).multiply(cos(vw),MC).add(cos(o.n).multiply(sin(vw),MC).multiply(cos(o.i),MC),MC),MC)); }
  private static BigDecimal kepler(BigDecimal m,BigDecimal e) { BigDecimal mr=rad(mod(m,C360)), x=mr; for(int i=0;i<24;i++){BigDecimal delta=x.subtract(e.multiply(sinRad(x),MC),MC).subtract(mr,MC).divide(BigDecimal.ONE.subtract(e.multiply(cosRad(x),MC),MC),MC);x=x.subtract(delta,MC);if(delta.abs().compareTo(new BigDecimal("1E-30"))<0)break;}return deg(x); }
  static BigDecimal sin(BigDecimal degrees){return sinRad(rad(degrees));} static BigDecimal cos(BigDecimal degrees){return cosRad(rad(degrees));} static BigDecimal tan(BigDecimal degrees){return sin(degrees).divide(cos(degrees),MC);} private static BigDecimal tanRad(BigDecimal radians){return sinRad(radians).divide(cosRad(radians),MC);} static BigDecimal rad(BigDecimal d){return d.multiply(D2R,MC);} static BigDecimal deg(BigDecimal r){return r.multiply(R2D,MC);} static BigDecimal mod(BigDecimal x,BigDecimal m){BigDecimal r=x.remainder(m);return r.signum()<0?r.add(m):r;}
  private static BigDecimal sinRad(BigDecimal x){x=mod(x.add(PI,MC),PI.multiply(new BigDecimal("2"),MC)).subtract(PI,MC);BigDecimal sum=x,term=x,xx=x.multiply(x,MC);for(int n=1;n<100;n++){term=term.multiply(xx,MC).divide(BigDecimal.valueOf((2L*n)*(2L*n+1L)),MC).negate();sum=sum.add(term,MC);if(term.abs().compareTo(new BigDecimal("1E-32"))<0)break;}return sum;}
  private static BigDecimal cosRad(BigDecimal x){return sinRad(x.add(HALF_PI,MC));}
  private static BigDecimal atan(BigDecimal x){if(x.signum()<0)return atan(x.negate()).negate();if(x.compareTo(new BigDecimal("0.5"))>0)return QUARTER_PI.add(atan(x.subtract(BigDecimal.ONE,MC).divide(x.add(BigDecimal.ONE,MC),MC)),MC);BigDecimal sum=x,term=x,xx=x.multiply(x,MC);for(int n=1;n<200;n++){term=term.multiply(xx,MC).negate();BigDecimal add=term.divide(BigDecimal.valueOf(2L*n+1L),MC);sum=sum.add(add,MC);if(add.abs().compareTo(new BigDecimal("1E-32"))<0)break;}return sum;}
  private static BigDecimal atan2(BigDecimal y,BigDecimal x){if(x.signum()>0)return atan(y.divide(x,MC));if(x.signum()<0)return y.signum()>=0?atan(y.divide(x,MC)).add(PI,MC):atan(y.divide(x,MC)).subtract(PI,MC);return y.signum()>0?HALF_PI:y.signum()<0?HALF_PI.negate():BigDecimal.ZERO;}
  private static BigDecimal sqrt(BigDecimal x){BigDecimal g=x.compareTo(BigDecimal.ONE)>0?x.divide(new BigDecimal("2"),MC):BigDecimal.ONE;for(int i=0;i<60;i++)g=g.add(x.divide(g,MC),MC).divide(new BigDecimal("2"),MC);return g;}
  private static BigDecimal add(String base,String rate,BigDecimal d){return new BigDecimal(base).add(new BigDecimal(rate).multiply(d,MC),MC);}
  private record Sun(BigDecimal lon,BigDecimal r,BigDecimal mean,BigDecimal peri){} private record Orbit(BigDecimal n,BigDecimal i,BigDecimal w,BigDecimal a,BigDecimal e,BigDecimal m){} private record Vec(BigDecimal x,BigDecimal y){}
}
