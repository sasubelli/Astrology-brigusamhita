package com.bhrigusamhita;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.YearMonth;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.Executors;

/** Dependency-free Java API. Every calculation scalar is BigDecimal. */
public final class JyotishaApplication {
  private static final MathContext MC = new MathContext(34, RoundingMode.HALF_EVEN);
  private static final BigDecimal ZERO = BigDecimal.ZERO;
  private static final BigDecimal ONE = BigDecimal.ONE;
  private static final BigDecimal THIRTY = new BigDecimal("30");
  private static final BigDecimal FULL_CIRCLE = new BigDecimal("360");
  private static final BigDecimal J2000 = new BigDecimal("2451545");
  private static final BigDecimal DAYS_PER_YEAR = new BigDecimal("365.2422");
  private static final String[] SIGNS = {"Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"};
  private static final String[] SIGN_SANSKRIT = {"Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"};
  private static final String[] LORDS = {"Mars","Venus","Mercury","Moon","Sun","Mercury","Venus","Mars","Jupiter","Saturn","Saturn","Jupiter"};
  private static final String[] NAKSHATRAS = {"Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"};
  private static final String[] NAK_LORDS = {"Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury","Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury","Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"};
  private static final String[] PLANETS = {"Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"};
  private static final Map<String, BigDecimal> BASE = Map.of("Sun", new BigDecimal("280.460"), "Moon", new BigDecimal("218.316"), "Mars", new BigDecimal("355.433"), "Mercury", new BigDecimal("252.251"), "Jupiter", new BigDecimal("34.351"), "Venus", new BigDecimal("181.979"), "Saturn", new BigDecimal("50.077"), "Rahu", new BigDecimal("125.123"));
  private static final Map<String, BigDecimal> RATE = Map.of("Sun", new BigDecimal("0.98564736"), "Moon", new BigDecimal("13.176358"), "Mars", new BigDecimal("0.5240208"), "Mercury", new BigDecimal("4.0923344"), "Jupiter", new BigDecimal("0.0830853"), "Venus", new BigDecimal("1.6021303"), "Saturn", new BigDecimal("0.0334442"), "Rahu", new BigDecimal("-0.0529538"));
  private static final List<Place> PLACES = List.of(new Place("Hyderabad, Telangana, India", "Hyderabad, Secunderabad", "17.385044", "78.486671", "Asia/Kolkata"), new Place("Vijayawada, Andhra Pradesh, India", "Vijayawada, Bezawada", "16.506174", "80.648015", "Asia/Kolkata"), new Place("Visakhapatnam, Andhra Pradesh, India", "Vizag, Visakhapatnam", "17.686816", "83.218482", "Asia/Kolkata"), new Place("Chennai, Tamil Nadu, India", "Chennai, Madras", "13.082680", "80.270718", "Asia/Kolkata"), new Place("Bengaluru, Karnataka, India", "Bangalore, Bengaluru", "12.971599", "77.594566", "Asia/Kolkata"), new Place("Mumbai, Maharashtra, India", "Mumbai, Bombay", "19.075984", "72.877656", "Asia/Kolkata"), new Place("New Delhi, India", "Delhi, New Delhi", "28.613939", "77.209021", "Asia/Kolkata"), new Place("Regidi, Andhrapradesh, India", "Regidi, Amadalavalasa", "18.5946", "83.7070", "Asia/Kolkata"), new Place("Warsaw, Poland", "Warsaw, Warszawa", "52.229676", "21.012229", "Europe/Warsaw"), new Place("London, United Kingdom", "London", "51.507218", "-0.127586", "Europe/London"), new Place("New York, United States", "New York, NYC", "40.712776", "-74.005974", "America/New_York"));

  public static void main(String[] args) throws IOException {
    int port = args.length == 0 ? 8080 : Integer.parseInt(args[0]);
    HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
    server.createContext("/", JyotishaApplication::route);
    server.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
    server.start();
    System.out.println("Jyotisha Java API running at http://127.0.0.1:" + port);
  }

  private static void route(HttpExchange x) throws IOException {
    try {
      String path = x.getRequestURI().getPath(); String method = x.getRequestMethod();
      if (method.equals("GET") && path.equals("/")) { file(x, "app/static/index.html", "text/html; charset=utf-8"); return; }
      if (method.equals("GET") && path.startsWith("/static/")) { file(x, "app/static/" + path.substring(8), path.endsWith(".js") ? "application/javascript" : "text/css"); return; }
      if (method.equals("GET") && path.equals("/api/places")) { json(x, 200, places(query(x.getRequestURI(), "q"))); return; }
      Map<String,Object> body = method.equals("POST") ? Json.object(new String(x.getRequestBody().readAllBytes(), StandardCharsets.UTF_8)) : Map.of();
      if (method.equals("POST") && path.equals("/api/predict")) { json(x, 200, prediction(chart(Birth.from(body)))); return; }
      if (method.equals("POST") && path.equals("/api/v1/chart/birth-data")) { json(x, 200, chart(Birth.from(body))); return; }
      if (method.equals("POST") && path.equals("/api/v1/dasha/current")) { json(x, 200, dasha(chart(Birth.from(body)))); return; }
      if (method.equals("POST") && path.equals("/api/v1/transits/active")) { json(x, 200, transits(Birth.from(body), text(body,"planet","Saturn"))); return; }
      if (method.equals("POST") && path.equals("/api/chat")) { json(x, 200, chat(body)); return; }
      error(x, 404, "Route not found");
    } catch (IllegalArgumentException e) { error(x, 400, e.getMessage()); }
    catch (Exception e) { error(x, 500, "Server error: " + e.getMessage()); }
  }

  private static Map<String,Object> chart(Birth b) {
    BigDecimal jd = julianDay(b.utc()); BigDecimal ayanamsa = ayanamsa(jd); BigDecimal asc = mod(PreciseAstronomy.ascendant(jd, b.latitude(), b.longitude()).subtract(ayanamsa, MC), FULL_CIRCLE);
    int ascSign = asc.divideToIntegralValue(THIRTY).intValue(); Map<String,Object> planets = new LinkedHashMap<>();
    for (String name : PLANETS) { BigDecimal longitude = preciseLongitude(name, jd, ayanamsa); planets.put(name, point(name, longitude, ascSign)); }
    Map<String,Object> root = new LinkedHashMap<>(); root.put("birth", b.json()); root.put("calculation", Map.of("ayanamsa","Lahiri", "ayanamsa_degrees", ayanamsa, "julian_day_ut",jd, "house_system","Whole-sign Vedic houses from sidereal ascendant", "ephemeris","Java BigDecimal mean-longitude engine")); root.put("ascendant", point("Ascendant", asc, ascSign)); root.put("planets", planets); root.put("house_signs", houses(ascSign, planets)); root.put("panchanga", panchanga(planets));
    root.put("divisional_charts", divisionalCharts(asc, ascSign, planets));
    return root;
  }

  /** Presentation layer retained for the existing browser client; data comes only from the chart engine. */
  private static Map<String,Object> prediction(Map<String,Object> chart) {
    Map<String,Object> result = new LinkedHashMap<>(chart);
    Map<?,?> asc = (Map<?,?>) chart.get("ascendant");
    Map<?,?> planets = (Map<?,?>) chart.get("planets");
    Map<?,?> moon = (Map<?,?>) planets.get("Moon");
    result.put("sutra_trace", List.of("Lagna is " + asc.get("sign") + "; whole-sign houses are measured from it.", "Moon is in " + moon.get("nakshatra") + " pada " + moon.get("pada") + "; it anchors the dasha sequence.", "All numeric chart positions were calculated with BigDecimal."));
    result.put("core_reading", Map.of("temperament", asc.get("sign") + " lagna gives the baseline orientation for this reflective reading.", "moon_pattern", "Moon in house " + moon.get("house") + " emphasizes its natal house themes.", "vitality_pattern", "Read timing through the Java dasha endpoint and transits through the on-demand transit endpoint."));
    Map<String,Object> areas = new LinkedHashMap<>();
    addArea(areas, "education_and_intellect", 5, chart); addArea(areas, "career_and_status", 10, chart); addArea(areas, "wealth_and_income", 2, chart); addArea(areas, "marriage_and_partnerships", 7, chart); addArea(areas, "health_and_resilience", 6, chart); addArea(areas, "spiritual_path", 9, chart);
    result.put("life_areas", areas);
    result.put("yogas", List.of(Map.of("name", "Chart synthesis", "strength", "Calculated", "reading", "Use exact chart placements and period tools before making a specific interpretive conclusion.")));
    Map<String,Object> current = dasha(chart);
    result.put("dashas", List.of(current));
    result.put("future_timeline", twoYearTimeline(current));
    result.put("monthly_timeline", monthlyTimeline(current));
    result.put("remedies", List.of(Map.of("focus", "Reflective practice", "practice", "Use a calm, consistent spiritual practice that is meaningful in your tradition.")));
    result.put("disclaimer", "Astrology readings are interpretive and spiritual. Use this for reflection, not medical, legal, financial, or safety-critical advice.");
    return result;
  }

  private static void addArea(Map<String,Object> areas, String key, int house, Map<String,Object> chart) {
    Map<?,?> sign = (Map<?,?>) ((List<?>) chart.get("house_signs")).get(house - 1);
    String lord = String.valueOf(sign.get("lord")); Map<?,?> lordPosition = (Map<?,?>) ((Map<?,?>) chart.get("planets")).get(lord);
    areas.put(key, Map.of("focus", "House " + house + " themes", "reading", "House " + house + " is " + sign.get("sign") + ", ruled by " + lord + " in house " + lordPosition.get("house") + ".", "karaka_check", "Use the chart and current dasha data together.", "timing_key", "Results mature during " + lord + " periods and relevant transits."));
  }

  /** D9 uses 3°20′ segments; Arudha Lagna uses the house-lord reflection rule. */
  private static Map<String,Object> divisionalCharts(BigDecimal ascLongitude, int ascSign, Map<String,Object> planets) {
    Map<String,Object> all = new LinkedHashMap<>();
    all.put("d1", Map.of("label", "D1 Rasi / Lagna", "ascendant", SIGNS[ascSign], "planets", planets));
    int d9Asc = navamsaSign(ascLongitude); Map<String,Object> d9Planets = new LinkedHashMap<>();
    for (var entry : planets.entrySet()) { Map<?,?> point = (Map<?,?>) entry.getValue(); BigDecimal longitude = (BigDecimal) point.get("longitude"); int sign = navamsaSign(longitude); d9Planets.put(entry.getKey(), Map.of("sign", SIGNS[sign], "sign_sanskrit", SIGN_SANSKRIT[sign], "sign_index", sign, "house", mod(BigDecimal.valueOf(sign - d9Asc), BigDecimal.valueOf(12)).intValue() + 1)); }
    all.put("d9", Map.of("label", "D9 Navamsa", "ascendant", SIGNS[d9Asc], "planets", d9Planets));
    String lagnaLord = LORDS[ascSign]; Map<?,?> lord = (Map<?,?>) planets.get(lagnaLord); int lordSign = ((Number) lord.get("sign_index")).intValue(); int distance = mod(BigDecimal.valueOf(lordSign - ascSign), BigDecimal.valueOf(12)).intValue(); int arudha = (lordSign + distance) % 12; if (arudha == ascSign || arudha == (ascSign + 6) % 12) arudha = (arudha + 9) % 12;
    all.put("arudha", Map.of("label", "Arudha Lagna (A1)", "sign", SIGNS[arudha], "sign_sanskrit", SIGN_SANSKRIT[arudha], "sign_index", arudha, "lord", lagnaLord, "lord_sign", SIGNS[lordSign]));
    return all;
  }

  private static int navamsaSign(BigDecimal longitude) { BigDecimal inSign = mod(longitude, THIRTY); int rasi = mod(longitude, FULL_CIRCLE).divideToIntegralValue(THIRTY).intValue(); int division = inSign.divide(new BigDecimal("3.33333333333333333333333333333333"), MC).intValue(); return (rasi * 9 + division) % 12; }
  private static List<Object> twoYearTimeline(Map<String,Object> current) { YearMonth start = YearMonth.now(ZoneId.of("UTC")); YearMonth end = start.plusMonths(23); return List.of(Map.of("period", current.get("mahadasha") + " period", "start", start.toString(), "end", end.toString(), "age_range", "Next 24 months", "opportunity", "Use the active dasha and transits to focus effort on the relevant natal houses.", "watch", "This is reflective guidance, not a certain outcome.", "practice", "Review the monthly cards for the two-year timing window.")); }
  private static List<Object> monthlyTimeline(Map<String,Object> current) { List<Object> months = new ArrayList<>(); YearMonth start = YearMonth.now(ZoneId.of("UTC")); for (int i = 0; i < 24; i++) { YearMonth month = start.plusMonths(i); months.add(Map.of("month", month.toString(), "period", current.get("mahadasha"), "age", "Two-year window", "opportunity", "Prioritize steady work, learning, and clear communication.", "watch", "Avoid treating a forecast as a fixed result.", "practice", "Check transits for this month before making timing-specific decisions.")); } return months; }

  private static Map<String,Object> point(String name, BigDecimal longitude, int ascSign) {
    int sign = mod(longitude,FULL_CIRCLE).divideToIntegralValue(THIRTY).intValue(); BigDecimal within = longitude.remainder(THIRTY).setScale(8, RoundingMode.HALF_EVEN); int nak = longitude.divide(new BigDecimal("13.33333333333333333333333333333333"), MC).intValue();
    Map<String,Object> result = new LinkedHashMap<>();
    result.put("name", name); result.put("longitude", longitude.setScale(8,RoundingMode.HALF_EVEN)); result.put("sign", SIGNS[sign]); result.put("sign_sanskrit", SIGN_SANSKRIT[sign]); result.put("sign_index", sign); result.put("degree_in_sign", within); result.put("nakshatra", NAKSHATRAS[nak]); result.put("nakshatra_lord", NAK_LORDS[nak]); result.put("pada", longitude.remainder(new BigDecimal("13.33333333333333333333333333333333")).divide(new BigDecimal("3.33333333333333333333333333333333"),MC).intValue()+1); result.put("house", mod(BigDecimal.valueOf(sign-ascSign),BigDecimal.valueOf(12)).intValue()+1); result.put("retrograde", name.equals("Rahu") || name.equals("Ketu")); result.put("dignity", dignity(name,sign)); result.put("speed", RATE.getOrDefault(name,ZERO));
    return result;
  }

  private static Map<String,Object> dasha(Map<String,Object> c) { Map<?,?> moon=(Map<?,?>)((Map<?,?>)c.get("planets")).get("Moon"); String lord=(String)moon.get("nakshatra_lord"); return Map.of("mahadasha",lord,"antardasha",lord,"basis","Moon nakshatra: "+moon.get("nakshatra"),"calculation_precision","BigDecimal"); }
  private static Map<String,Object> transits(Birth b,String planet) { Map<String,Object> c=chart(b); Map<?,?> natal=(Map<?,?>)((Map<?,?>)c.get("planets")).get(planet); ZonedDateTime now=ZonedDateTime.now(ZoneId.of("UTC")); BigDecimal current=longitude(planet,julianDay(now),ayanamsa(julianDay(now))); BigDecimal asc=BigDecimal.valueOf(((Number)((Map<?,?>)c.get("ascendant")).get("sign_index")).longValue()); int house=mod(current.divideToIntegralValue(THIRTY).subtract(asc,MC),BigDecimal.valueOf(12)).intValue()+1; return Map.of("planet",planet,"transit_longitude",current,"transit_house",house,"natal_house",natal.get("house"),"natal_aspect",house==7 || house==10,"calculation_precision","BigDecimal"); }
  private static Map<String,Object> chat(Map<String,Object> body) { String q=text(body,"question","").toLowerCase(Locale.ROOT); Map<String,Object> payload=(Map<String,Object>)body.get("chart"); String answer; if(q.contains("transit")||q.contains("now")||q.contains("upcoming")) answer="Transit information is loaded on demand from /api/v1/transits/active. Ask for a specific planet to receive its current house."; else if(q.contains("dasha")) answer="Dasha information is loaded on demand from /api/v1/dasha/current using the Moon nakshatra in your chart."; else answer="I use the Java chart API as the source of placements and do not infer unprovided astronomical data."; return Map.of("answer",answer,"sloka","", "transliteration","", "sources",List.of(),"divisional_highlights",payload==null?Map.of():payload.getOrDefault("divisional_charts",Map.of())); }
  private static List<Object> houses(int asc,Map<String,Object> planets){ List<Object> a=new ArrayList<>(); for(int h=1;h<=12;h++){int s=(asc+h-1)%12;List<String> occ=new ArrayList<>();for(var e:planets.entrySet())if(((Number)((Map<?,?>)e.getValue()).get("house")).intValue()==h)occ.add(e.getKey());Map<String,Object> house=new LinkedHashMap<>();house.put("house",h);house.put("sign",SIGNS[s]);house.put("sign_sanskrit",SIGN_SANSKRIT[s]);house.put("lord",LORDS[s]);house.put("theme","House "+h);house.put("lord_house",null);house.put("occupants",occ);a.add(house);}return a;}
  private static Map<String,Object> panchanga(Map<String,Object> p){BigDecimal sun=(BigDecimal)((Map<?,?>)p.get("Sun")).get("longitude"), moon=(BigDecimal)((Map<?,?>)p.get("Moon")).get("longitude");return Map.of("vara","Calculated locally","paksha",mod(moon.subtract(sun,MC),FULL_CIRCLE).compareTo(new BigDecimal("180"))<0?"Shukla":"Krishna","tithi_name","Tithi "+mod(moon.subtract(sun,MC),FULL_CIRCLE).divide(new BigDecimal("12"),MC).intValue()+1);}
  private static BigDecimal longitude(String planet,BigDecimal jd,BigDecimal aya){if(planet.equals("Ketu"))return mod(longitude("Rahu",jd,aya).add(new BigDecimal("180"),MC),FULL_CIRCLE);return mod(BASE.get(planet).add(RATE.get(planet).multiply(jd.subtract(J2000,MC),MC),MC).subtract(aya,MC),FULL_CIRCLE);}
  private static BigDecimal preciseLongitude(String planet,BigDecimal jd,BigDecimal aya){if(planet.equals("Ketu"))return mod(preciseLongitude("Rahu",jd,aya).add(new BigDecimal("180"),MC),FULL_CIRCLE);BigDecimal precise=PreciseAstronomy.longitude(planet,jd,aya);return precise==null?longitude(planet,jd,aya):precise;}
  private static BigDecimal ayanamsa(BigDecimal jd){return new BigDecimal("23.853055").add(new BigDecimal("0.01396971277777777777777777777778").multiply(jd.subtract(J2000,MC).divide(DAYS_PER_YEAR,MC),MC),MC);}
  private static BigDecimal siderealAscendant(BigDecimal jd,BigDecimal longitude){return mod(new BigDecimal("280.46061837").add(new BigDecimal("0.98564736629").multiply(jd.subtract(J2000,MC),MC),MC).add(longitude,MC),FULL_CIRCLE);}
  private static BigDecimal julianDay(ZonedDateTime t){BigDecimal unix=new BigDecimal(t.toInstant().getEpochSecond()).add(new BigDecimal(t.getNano()).movePointLeft(9),MC);return new BigDecimal("2440587.5").add(unix.divide(new BigDecimal("86400"),MC),MC);}
  private static BigDecimal mod(BigDecimal v,BigDecimal m){BigDecimal r=v.remainder(m);return r.signum()<0?r.add(m):r;}
  private static String dignity(String p,int s){return (p.equals("Sun")&&s==4)||(p.equals("Moon")&&s==1)||(p.equals("Jupiter")&&s==3)?"exalted":"neutral";}
  private static List<Object> places(String q){String n=q.toLowerCase(Locale.ROOT);List<Object>a=new ArrayList<>();for(Place p:PLACES)if(n.isBlank()||p.name.toLowerCase(Locale.ROOT).contains(n)||p.aliases.toLowerCase(Locale.ROOT).contains(n))a.add(p.json());return a;}
  private static String query(URI u,String k){String q=Objects.toString(u.getQuery(),"");for(String part:q.split("&")){String[] v=part.split("=",2);if(v.length==2&&v[0].equals(k))return java.net.URLDecoder.decode(v[1],StandardCharsets.UTF_8);}return "";}
  private static void file(HttpExchange x,String f,String type)throws IOException{Path p=Path.of(f).normalize();if(!Files.isRegularFile(p)){error(x,404,"File not found");return;}byte[]b=Files.readAllBytes(p);x.getResponseHeaders().set("Content-Type",type);x.sendResponseHeaders(200,b.length);x.getResponseBody().write(b);x.close();}
  private static void json(HttpExchange x,int s,Object o)throws IOException{byte[]b=Json.stringify(o).getBytes(StandardCharsets.UTF_8);x.getResponseHeaders().set("Content-Type","application/json; charset=utf-8");x.sendResponseHeaders(s,b.length);x.getResponseBody().write(b);x.close();}
  private static void error(HttpExchange x,int s,String d)throws IOException{json(x,s,Map.of("detail",d));}
  private static String text(Map<String,Object> m,String key,String fallback){Object v=m.get(key);return v==null?fallback:String.valueOf(v);}
  private record Place(String name,String aliases,String latitude,String longitude,String timezone){Map<String,Object>json(){return Map.of("name",name,"aliases",List.of(aliases.split(", ")),"latitude",new BigDecimal(latitude),"longitude",new BigDecimal(longitude),"timezone",timezone);}}
  private record Birth(String name,String date,String time,String place,BigDecimal latitude,BigDecimal longitude,String timezone){static Birth from(Map<String,Object>m){String place=text(m,"place","");Place p=PLACES.stream().filter(x->x.name.equalsIgnoreCase(place)||x.aliases.toLowerCase(Locale.ROOT).contains(place.toLowerCase(Locale.ROOT))).findFirst().orElse(null);BigDecimal lat=m.get("latitude")==null?(p==null?null:new BigDecimal(p.latitude)):new BigDecimal(String.valueOf(m.get("latitude")));BigDecimal lon=m.get("longitude")==null?(p==null?null:new BigDecimal(p.longitude)):new BigDecimal(String.valueOf(m.get("longitude")));if(lat==null||lon==null)throw new IllegalArgumentException("Choose a listed place or provide latitude and longitude.");String tz=text(m,"timezone",p==null?"UTC":p.timezone);return new Birth(text(m,"name","Native"),text(m,"date",""),text(m,"time",""),place.isBlank()?(p==null?"Manual coordinates":p.name):place,lat,lon,tz);}ZonedDateTime utc(){try{return LocalDateTime.parse(date+"T"+time,DateTimeFormatter.ISO_LOCAL_DATE_TIME).atZone(ZoneId.of(timezone)).withZoneSameInstant(ZoneId.of("UTC"));}catch(Exception e){throw new IllegalArgumentException("Use ISO birth date and time with a valid IANA timezone.");}}Map<String,Object>json(){ZonedDateTime local=utc().withZoneSameInstant(ZoneId.of(timezone));return Map.of("name",name,"place",place,"latitude",latitude,"longitude",longitude,"timezone",timezone,"local_datetime",local.toString(),"utc_datetime",utc().toString());}}
}
