package com.bhrigusamhita;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Small JSON codec: numeric JSON tokens are parsed as BigDecimal, never floating point. */
final class Json {
  static Map<String,Object> object(String input) { Object value = new Parser(input).value(); if (!(value instanceof Map<?,?> map)) throw new IllegalArgumentException("JSON object required"); Map<String,Object> out = new LinkedHashMap<>(); map.forEach((k,v) -> out.put(String.valueOf(k),v)); return out; }
  static String stringify(Object v) { if(v==null)return "null"; if(v instanceof String s)return '"'+escape(s)+'"'; if(v instanceof Number||v instanceof Boolean)return v.toString(); if(v instanceof Map<?,?> m){List<String>a=new ArrayList<>();m.forEach((k,x)->a.add(stringify(k.toString())+":"+stringify(x)));return "{"+String.join(",",a)+"}";} if(v instanceof Iterable<?> it){List<String>a=new ArrayList<>();it.forEach(x->a.add(stringify(x)));return "["+String.join(",",a)+"]";} return stringify(v.toString()); }
  private static String escape(String s){return s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r");}
  private static final class Parser { final String s; int i; Parser(String s){this.s=s.trim();} Object value(){ws();char c=peek();if(c=='{')return obj();if(c=='[')return arr();if(c=='\"')return str();if(c=='t'){i+=4;return true;}if(c=='f'){i+=5;return false;}if(c=='n'){i+=4;return null;}return num();} Map<String,Object> obj(){Map<String,Object>m=new LinkedHashMap<>();i++;ws();if(peek()=='}'){i++;return m;}while(true){String k=str();ws();expect(':');Object v=value();m.put(k,v);ws();if(peek()=='}'){i++;return m;}expect(',');ws();}} List<Object> arr(){List<Object>a=new ArrayList<>();i++;ws();if(peek()==']'){i++;return a;}while(true){a.add(value());ws();if(peek()==']'){i++;return a;}expect(',');}} String str(){expect('\"');StringBuilder b=new StringBuilder();while(peek()!='\"'){char c=s.charAt(i++);if(c=='\\'){char e=s.charAt(i++);b.append(e=='n'?'\n':e=='r'?'\r':e=='t'?'\t':e);}else b.append(c);}i++;return b.toString();} BigDecimal num(){int start=i;while(i<s.length()&&"-+0123456789.eE".indexOf(s.charAt(i))>=0)i++;return new BigDecimal(s.substring(start,i));} void ws(){while(i<s.length()&&Character.isWhitespace(s.charAt(i)))i++;} char peek(){ws();if(i>=s.length())throw new IllegalArgumentException("Invalid JSON");return s.charAt(i);}void expect(char c){if(peek()!=c)throw new IllegalArgumentException("Invalid JSON");i++;}}
}
