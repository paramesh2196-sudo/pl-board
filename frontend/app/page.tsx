'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import {
  Search, MapPin, Briefcase, Calendar, ExternalLink, RefreshCw,
  Filter, X, Building2, Star, Globe, Zap, ChevronDown, ChevronUp,
  Bookmark, BookmarkMinus, ArrowUpDown, Users, Clock, Download,
  GraduationCap, TrendingUp, Layers, IndianRupee, Wifi, Check
} from 'lucide-react';

// ==================== Types ====================
interface Job {
  id: number;
  title: string;
  company: string;
  city: string;
  state: string | null;
  country: string | null;
  location_full: string | null;
  description: string | null;
  url: string;
  domain: string | null;
  technology: string | null;
  experience_range: string | null;
  job_type: string | null;
  is_remote: boolean;
  is_walkin: boolean;
  min_salary: number | null;
  max_salary: number | null;
  salary_currency: string | null;
  salary_period: string | null;
  company_industry: string | null;
  company_logo: string | null;
  company_url: string | null;
  company_rating: number | null;
  company_reviews_count: number | null;
  company_num_employees: string | null;
  skills: string | null;
  vacancy_count: number | null;
  emails: string | null;
  date_posted: string | null;
  posted_date: string | null;
  source: string;
  job_url_direct: string | null;
}

interface PaginatedResponse {
  jobs: Job[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

interface Stats {
  total_jobs: number;
  jobs_today: number;
  cities_count: number;
  walkin_count: number;
  sources: Record<string, number>;
  domains: Record<string, number>;
  cities: Record<string, number>;
  experiences: Record<string, number>;
  last_scrape_time: string | null;
  is_scraping: boolean;
}

// ==================== Constants ====================
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

const CITIES = ["Bangalore", "Hyderabad", "Chennai", "Kolkata", "Mumbai", "Pune", "Gurgaon"];
const TECHNOLOGIES = [
  "Python", "Java", "JavaScript", "React", "Angular", "Node.js",
  "SQL", "AWS", ".NET", "C++", "DevOps", "Docker",
  "Machine Learning", "Data Science", "Flutter", "Android",
  "Testing", "Selenium", "SAP", "PHP",
];
const EXPERIENCE_OPTIONS = [
  { value: "", label: "All Experience" },
  { value: "fresher", label: "Fresher / 0 years" },
  { value: "1", label: "1 year" },
  { value: "2", label: "2 years" },
  { value: "3", label: "3 years" },
  { value: "0-1", label: "0-1 years" },
  { value: "0-2", label: "0-2 years" },
  { value: "1-3", label: "1-3 years" },
  { value: "2-5", label: "2-5 years" },
  { value: "3-5", label: "3-5 years" },
  { value: "5+", label: "5+ years" },
];
const SORT_OPTIONS = [
  { value: "newest", label: "Newest First" },
  { value: "salary_high", label: "Salary: High to Low" },
  { value: "salary_low", label: "Salary: Low to High" },
  { value: "company", label: "Company A-Z" },
];
const SOURCE_COLORS: Record<string, string> = {
  indeed: "bg-blue-100 text-blue-700 border-blue-200",
  linkedin: "bg-sky-100 text-sky-700 border-sky-200",
  naukri: "bg-indigo-100 text-indigo-700 border-indigo-200",
  google: "bg-red-100 text-red-700 border-red-200",
  glassdoor: "bg-green-100 text-green-700 border-green-200",
  internshala: "bg-purple-100 text-purple-700 border-purple-200",
  timesjobs: "bg-orange-100 text-orange-700 border-orange-200",
  freshersworld: "bg-teal-100 text-teal-700 border-teal-200",
};
const DOMAIN_ICONS: Record<string, string> = {
  "IT-Software": "\u{1F4BB}", "Data Science": "\u{1F4CA}", "Web Development": "\u{1F310}",
  "Mobile Development": "\u{1F4F1}", "Testing/QA": "\u{1F9EA}", "Database/DBA": "\u{1F5C4}\uFE0F",
  "Cloud/DevOps": "\u2601\uFE0F", "Networking": "\u{1F50C}", "Design/UI-UX": "\u{1F3A8}",
  "Sales/Marketing": "\u{1F4E2}", "Finance/Accounting": "\u{1F4B0}", "HR/Recruitment": "\u{1F465}",
  "Content/Writing": "\u270D\uFE0F", "Support/BPO": "\u{1F4DE}", "Management": "\u{1F4CB}",
  "Mechanical/Civil": "\u2699\uFE0F", "Electrical/Electronics": "\u26A1", "General": "\u{1F4C1}",
};
const PAGE_SIZE = 30;

// ==================== Component ====================
export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [showFilters, setShowFilters] = useState(true);
  const [expandedJob, setExpandedJob] = useState<number | null>(null);
  const [totalJobs, setTotalJobs] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [currentOffset, setCurrentOffset] = useState(0);
  const [bookmarks, setBookmarks] = useState<Set<number>>(new Set());
  const [showBookmarksOnly, setShowBookmarksOnly] = useState(false);
  const [activeFiltersCount, setActiveFiltersCount] = useState(0);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const [filters, setFilters] = useState({
    city: '', technology: '', domain: '', source: '',
    search: '', experience: '', job_type: '',
    is_walkin: '', is_remote: '', days: '7', sort: 'newest',
  });

  useEffect(() => {
    try {
      const saved = localStorage.getItem('plboard_bookmarks');
      if (saved) setBookmarks(new Set(JSON.parse(saved)));
    } catch {}
  }, []);

  useEffect(() => {
    let count = 0;
    if (filters.city) count++;
    if (filters.technology) count++;
    if (filters.domain) count++;
    if (filters.source) count++;
    if (filters.experience) count++;
    if (filters.job_type) count++;
    if (filters.is_walkin === 'true') count++;
    if (filters.is_remote === 'true') count++;
    if (filters.search) count++;
    setActiveFiltersCount(count);
  }, [filters]);

  const buildParams = useCallback((offset: number) => {
    const params = new URLSearchParams();
    if (filters.city) params.append('city', filters.city);
    if (filters.technology) params.append('technology', filters.technology);
    if (filters.domain) params.append('domain', filters.domain);
    if (filters.source) params.append('source', filters.source);
    if (filters.search) params.append('search', filters.search);
    if (filters.experience) params.append('experience', filters.experience);
    if (filters.job_type) params.append('job_type', filters.job_type);
    if (filters.is_walkin === 'true') params.append('is_walkin', 'true');
    if (filters.is_remote === 'true') params.append('is_remote', 'true');
    params.append('sort', filters.sort);
    params.append('days', filters.days);
    params.append('limit', String(PAGE_SIZE));
    params.append('offset', String(offset));
    return params;
  }, [filters]);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    setCurrentOffset(0);
    try {
      const params = buildParams(0);
      const res = await axios.get<PaginatedResponse>(`${API_BASE}/jobs?${params.toString()}`);
      setJobs(res.data.jobs);
      setTotalJobs(res.data.total);
      setHasMore(res.data.has_more);
      setCurrentOffset(PAGE_SIZE);
    } catch (error) {
      console.error("Error fetching jobs:", error);
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const params = buildParams(currentOffset);
      const res = await axios.get<PaginatedResponse>(`${API_BASE}/jobs?${params.toString()}`);
      setJobs(prev => [...prev, ...res.data.jobs]);
      setHasMore(res.data.has_more);
      setCurrentOffset(prev => prev + PAGE_SIZE);
    } catch (error) {
      console.error("Error loading more:", error);
    } finally {
      setLoadingMore(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await axios.get(`${API_BASE}/stats`);
      setStats(res.data);
      if (triggering && !res.data.is_scraping) {
        setTriggering(false);
        fetchJobs();
      }
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  };

  const triggerScrape = async () => {
    setTriggering(true);
    try {
      await axios.post(`${API_BASE}/trigger-scrape`);
      if (pollingRef.current) clearInterval(pollingRef.current);
      pollingRef.current = setInterval(() => { fetchStats(); }, 5000);
    } catch (error) {
      console.error("Error triggering scrape:", error);
      setTriggering(false);
    }
  };

  useEffect(() => {
    if (stats && !stats.is_scraping && pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
      if (triggering) { setTriggering(false); fetchJobs(); }
    }
  }, [stats?.is_scraping]);

  const resetFilters = () => {
    setFilters({
      city: '', technology: '', domain: '', source: '',
      search: '', experience: '', job_type: '',
      is_walkin: '', is_remote: '', days: '7', sort: 'newest',
    });
  };

  const toggleBookmark = (jobId: number) => {
    setBookmarks(prev => {
      const next = new Set(prev);
      if (next.has(jobId)) next.delete(jobId); else next.add(jobId);
      localStorage.setItem('plboard_bookmarks', JSON.stringify([...next]));
      return next;
    });
  };

  const exportCSV = () => {
    const dj = showBookmarksOnly ? jobs.filter(j => bookmarks.has(j.id)) : jobs;
    const headers = ['Title','Company','City','Domain','Experience','Salary','Source','URL','Walk-in','Posted'];
    const rows = dj.map(j => [
      `"${(j.title||'').replace(/"/g,'""')}"`, `"${(j.company||'').replace(/"/g,'""')}"`,
      j.city||'', j.domain||'', j.experience_range||'Fresher', formatSalary(j)||'',
      j.source||'', j.url||'', j.is_walkin?'Yes':'No', j.date_posted||'',
    ]);
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = `plboard-jobs-${new Date().toISOString().split('T')[0]}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  // Auto-apply filters when any filter value changes
  const isFirstRender = useRef(true);
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    const debounceTimer = setTimeout(() => {
      fetchJobs();
    }, filters.search ? 400 : 50);
    return () => clearTimeout(debounceTimer);
  }, [filters.city, filters.technology, filters.domain, filters.source, filters.experience, filters.job_type, filters.is_walkin, filters.is_remote, filters.days, filters.sort, filters.search]);

  useEffect(() => {
    fetchJobs(); fetchStats();
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, []);

  const formatSalary = (job: Job) => {
    if (!job.min_salary && !job.max_salary) return null;
    const currency = job.salary_currency || '\u20B9';
    const fmt = (n: number) => {
      if (n >= 100000) return `${(n/100000).toFixed(1)}L`;
      if (n >= 1000) return `${(n/1000).toFixed(0)}K`;
      return n.toLocaleString();
    };
    if (job.min_salary && job.max_salary) return `${currency} ${fmt(job.min_salary)} - ${fmt(job.max_salary)}`;
    if (job.min_salary) return `${currency} ${fmt(job.min_salary)}+`;
    if (job.max_salary) return `Up to ${currency} ${fmt(job.max_salary)}`;
    return null;
  };

  const timeAgo = (dateStr: string | null) => {
    if (!dateStr) return 'Recently';
    const diff = Date.now() - new Date(dateStr).getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days === 1) return '1 day ago';
    if (days < 7) return `${days} days ago`;
    return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  };

  const formatLastScrape = (iso: string | null) => {
    if (!iso) return 'Never';
    return new Date(iso).toLocaleString('en-IN', { day:'numeric', month:'short', hour:'2-digit', minute:'2-digit' });
  };

  const displayJobs = showBookmarksOnly ? jobs.filter(j => bookmarks.has(j.id)) : jobs;

  return (
    <main className="max-w-[1400px] mx-auto p-4 md:p-6">
      {/* Header */}
      <header className="mb-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">PL Board</h1>
            {stats?.last_scrape_time && (
              <p className="text-[11px] text-gray-400 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Last updated: {formatLastScrape(stats.last_scrape_time)}
              </p>
            )}
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => setShowBookmarksOnly(!showBookmarksOnly)}
            className={`border px-3 py-2 rounded-lg text-sm flex items-center gap-1.5 transition ${showBookmarksOnly ? 'bg-amber-50 border-amber-300 text-amber-700' : 'border-gray-200 hover:bg-gray-50 text-gray-600'}`}>
            {showBookmarksOnly ? <><Bookmark className="w-4 h-4 fill-amber-500" /></> : <Bookmark className="w-4 h-4" />}
            Saved ({bookmarks.size})
          </button>
          <button onClick={exportCSV}
            className="border border-gray-200 px-3 py-2 rounded-lg text-sm hover:bg-gray-50 flex items-center gap-1.5 text-gray-600">
            <Download className="w-4 h-4" /> Export
          </button>
          <button onClick={() => setShowFilters(!showFilters)}
            className={`border px-3 py-2 rounded-lg text-sm flex items-center gap-1.5 transition ${showFilters ? 'bg-gray-800 text-white border-gray-800' : 'border-gray-200 hover:bg-gray-50 text-gray-600'}`}>
            <Filter className="w-4 h-4" /> Filters
            {activeFiltersCount > 0 && (
              <span className="bg-blue-500 text-white text-[10px] w-4 h-4 rounded-full flex items-center justify-center">
                {activeFiltersCount}
              </span>
            )}
          </button>
          <button onClick={triggerScrape} disabled={triggering}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-60 flex items-center gap-2 text-sm font-medium shadow-sm">
            <RefreshCw className={`w-4 h-4 ${triggering ? 'animate-spin' : ''}`} />
            {triggering ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </header>

      {/* Refreshing Banner */}
      {(triggering || stats?.is_scraping) && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 flex items-center gap-3 animate-pulse">
          <RefreshCw className="w-5 h-5 animate-spin text-blue-600" />
          <div>
            <p className="text-sm font-medium text-blue-800">Refreshing jobs...</p>
            <p className="text-xs text-blue-600">Fetching latest jobs from all sources. This may take a few minutes.</p>
          </div>
          {stats && <span className="ml-auto text-sm font-bold text-blue-700">{stats.total_jobs} jobs</span>}
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-5">
          <div className="bg-white p-3.5 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition">
            <div className="flex items-center justify-between">
              <p className="text-2xl font-bold text-blue-600">{stats.total_jobs.toLocaleString()}</p>
              <Briefcase className="w-5 h-5 text-blue-300" />
            </div>
            <p className="text-[11px] text-gray-500 mt-0.5">Total Jobs</p>
          </div>
          <div className="bg-white p-3.5 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition">
            <div className="flex items-center justify-between">
              <p className="text-2xl font-bold text-green-600">{stats.walkin_count.toLocaleString()}</p>
              <Users className="w-5 h-5 text-green-300" />
            </div>
            <p className="text-[11px] text-gray-500 mt-0.5">Walk-in Drives</p>
          </div>
          <div className="bg-white p-3.5 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition">
            <div className="flex items-center justify-between">
              <p className="text-2xl font-bold text-purple-600">{stats.cities_count}</p>
              <MapPin className="w-5 h-5 text-purple-300" />
            </div>
            <p className="text-[11px] text-gray-500 mt-0.5">Cities</p>
          </div>
          <div className="bg-white p-3.5 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition">
            <div className="flex items-center justify-between">
              <p className="text-2xl font-bold text-orange-600">{Object.keys(stats.sources).length}</p>
              <Globe className="w-5 h-5 text-orange-300" />
            </div>
            <p className="text-[11px] text-gray-500 mt-0.5">Sources Active</p>
          </div>
          <div className="bg-white p-3.5 rounded-lg shadow-sm border border-gray-100 hover:shadow-md transition col-span-2 sm:col-span-1">
            <div className="flex items-center justify-between">
              <p className="text-2xl font-bold text-teal-600">{stats.jobs_today.toLocaleString()}</p>
              <TrendingUp className="w-5 h-5 text-teal-300" />
            </div>
            <p className="text-[11px] text-gray-500 mt-0.5">Added Today</p>
          </div>
        </div>
      )}

      {/* Source Chips */}
      {stats && Object.keys(stats.sources).length > 0 && (
        <div className="flex flex-wrap gap-2 mb-5">
          {Object.entries(stats.sources).sort((a, b) => b[1] - a[1]).map(([src, cnt]) => (
            <button key={src}
              onClick={() => { setFilters(f => ({ ...f, source: f.source === src ? '' : src })); }}
              className={`text-xs px-3 py-1.5 rounded-full border font-medium transition cursor-pointer
                ${filters.source === src ? 'ring-2 ring-offset-1 ring-blue-400' : ''}
                ${SOURCE_COLORS[src] || 'bg-gray-100 text-gray-600 border-gray-200'}`}>
              {src.charAt(0).toUpperCase() + src.slice(1)}: {cnt}
            </button>
          ))}
        </div>
      )}

      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 mb-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-3">
            <div className="flex items-center border rounded-lg px-3 py-2 sm:col-span-2 focus-within:ring-2 focus-within:ring-blue-200 focus-within:border-blue-400 transition">
              <Search className="w-4 h-4 text-gray-400 mr-2 shrink-0" />
              <input type="text" placeholder="Search jobs, companies, skills..."
                className="w-full outline-none text-sm" value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && fetchJobs()} />
              {filters.search && (
                <button onClick={() => setFilters({ ...filters, search: '' })} className="text-gray-400 hover:text-gray-600">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <div className="flex items-center border rounded-lg px-3 py-2 focus-within:ring-2 focus-within:ring-blue-200 transition">
              <MapPin className="w-4 h-4 text-gray-400 mr-2 shrink-0" />
              <select className="w-full outline-none text-sm bg-transparent" value={filters.city}
                onChange={(e) => setFilters({ ...filters, city: e.target.value })}>
                <option value="">All Cities</option>
                {CITIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="flex items-center border rounded-lg px-3 py-2 focus-within:ring-2 focus-within:ring-blue-200 transition">
              <GraduationCap className="w-4 h-4 text-gray-400 mr-2 shrink-0" />
              <select className="w-full outline-none text-sm bg-transparent" value={filters.experience}
                onChange={(e) => setFilters({ ...filters, experience: e.target.value })}>
                {EXPERIENCE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="flex items-center border rounded-lg px-3 py-2 focus-within:ring-2 focus-within:ring-blue-200 transition">
              <Layers className="w-4 h-4 text-gray-400 mr-2 shrink-0" />
              <select className="w-full outline-none text-sm bg-transparent" value={filters.technology}
                onChange={(e) => setFilters({ ...filters, technology: e.target.value })}>
                <option value="">All Technologies</option>
                {TECHNOLOGIES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="flex items-center border rounded-lg px-3 py-2 focus-within:ring-2 focus-within:ring-blue-200 transition">
              <Briefcase className="w-4 h-4 text-gray-400 mr-2 shrink-0" />
              <select className="w-full outline-none text-sm bg-transparent" value={filters.domain}
                onChange={(e) => setFilters({ ...filters, domain: e.target.value })}>
                <option value="">All Domains</option>
                {Object.keys(DOMAIN_ICONS).map(d => (
                  <option key={d} value={d}>{DOMAIN_ICONS[d]} {d}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center border rounded-lg px-3 py-2 focus-within:ring-2 focus-within:ring-blue-200 transition">
              <Globe className="w-4 h-4 text-gray-400 mr-2 shrink-0" />
              <select className="w-full outline-none text-sm bg-transparent" value={filters.source}
                onChange={(e) => setFilters({ ...filters, source: e.target.value })}>
                <option value="">All Sources</option>
                {Object.keys(SOURCE_COLORS).map(s => (
                  <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center border rounded-lg px-3 py-2 focus-within:ring-2 focus-within:ring-blue-200 transition">
              <Calendar className="w-4 h-4 text-gray-400 mr-2 shrink-0" />
              <select className="w-full outline-none text-sm bg-transparent" value={filters.days}
                onChange={(e) => setFilters({ ...filters, days: e.target.value })}>
                <option value="1">Last 24 hours</option>
                <option value="3">Last 3 days</option>
                <option value="7">Last 7 days</option>
                <option value="14">Last 14 days</option>
                <option value="30">Last 30 days</option>
              </select>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3 mb-3">
            <label className="flex items-center gap-2 text-sm cursor-pointer select-none px-3 py-1.5 rounded-lg border hover:bg-gray-50 transition">
              <input type="checkbox" checked={filters.is_walkin === 'true'}
                onChange={(e) => setFilters({ ...filters, is_walkin: e.target.checked ? 'true' : '' })}
                className="rounded accent-green-600" />
              <span className="text-green-700 font-medium">{'\u{1F6B6}'} Walk-in Only</span>
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer select-none px-3 py-1.5 rounded-lg border hover:bg-gray-50 transition">
              <input type="checkbox" checked={filters.is_remote === 'true'}
                onChange={(e) => setFilters({ ...filters, is_remote: e.target.checked ? 'true' : '' })}
                className="rounded accent-violet-600" />
              <span className="text-violet-700 font-medium"><Wifi className="w-3.5 h-3.5 inline mr-0.5" /> Remote Only</span>
            </label>
            <div className="flex items-center gap-1.5 ml-auto border rounded-lg px-3 py-1.5">
              <ArrowUpDown className="w-3.5 h-3.5 text-gray-400" />
              <select className="outline-none text-sm bg-transparent" value={filters.sort}
                onChange={(e) => setFilters({ ...filters, sort: e.target.value })}>
                {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={resetFilters}
              className="text-gray-500 px-3 py-1.5 rounded-lg text-sm hover:bg-gray-100 flex items-center gap-1 transition">
              <X className="w-3 h-3" /> Clear All
            </button>
            <button onClick={fetchJobs}
              className="bg-gray-800 text-white rounded-lg px-5 py-1.5 text-sm hover:bg-gray-900 font-medium transition">
              Apply Filters
            </button>
          </div>
        </div>
      )}

      {/* Results Header */}
      <div className="mb-4 flex justify-between items-center">
        <p className="text-sm text-gray-500">
          {loading ? 'Loading...' : (
            showBookmarksOnly
              ? `${displayJobs.length} saved job${displayJobs.length !== 1 ? 's' : ''}`
              : <><span className="font-semibold text-gray-700">{totalJobs.toLocaleString()}</span> jobs found {'\u00B7'} Showing {Math.min(jobs.length, totalJobs)}</>
          )}
        </p>
        {activeFiltersCount > 0 && (
          <button onClick={() => { resetFilters(); setTimeout(fetchJobs, 100); }}
            className="text-xs text-blue-600 hover:underline">
            Clear {activeFiltersCount} filter{activeFiltersCount > 1 ? 's' : ''}
          </button>
        )}
      </div>

      {/* Job Grid */}
      {loading ? (
        <div className="text-center py-20">
          <RefreshCw className="w-10 h-10 animate-spin mx-auto text-blue-400 mb-4" />
          <p className="text-gray-400 text-lg">Loading jobs...</p>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {displayJobs.map((job) => (
              <div key={job.id}
                className="bg-white p-5 rounded-xl shadow-sm hover:shadow-lg transition-all duration-200 border border-gray-100 flex flex-col group">
                <div className="flex justify-between items-start mb-2 gap-2">
                  <div className="flex gap-1 flex-wrap">
                    {job.is_walkin && (
                      <span className="bg-green-100 text-green-700 text-[10px] px-2 py-0.5 rounded-full font-semibold border border-green-200">
                        {'\u{1F6B6}'} Walk-in
                      </span>
                    )}
                    {job.is_remote && (
                      <span className="bg-violet-100 text-violet-700 text-[10px] px-2 py-0.5 rounded-full font-semibold border border-violet-200">
                        Remote
                      </span>
                    )}
                    {job.vacancy_count && job.vacancy_count > 1 && (
                      <span className="bg-amber-50 text-amber-700 text-[10px] px-2 py-0.5 rounded-full font-medium border border-amber-200">
                        {job.vacancy_count} openings
                      </span>
                    )}
                  </div>
                  <button onClick={() => toggleBookmark(job.id)}
                    className="opacity-40 group-hover:opacity-100 transition-opacity shrink-0">
                    {bookmarks.has(job.id) ? (
                      <Bookmark className="w-4 h-4 text-amber-500 fill-amber-500" />
                    ) : (
                      <Bookmark className="w-4 h-4 text-gray-400 hover:text-amber-500" />
                    )}
                  </button>
                </div>
                <h3 className="font-semibold text-gray-800 line-clamp-2 text-[15px] leading-snug mb-2">{job.title}</h3>
                <div className="flex items-center gap-2 mb-3">
                  {job.company_logo ? (
                    <img src={job.company_logo} alt="" className="w-6 h-6 rounded object-contain bg-gray-50" />
                  ) : (
                    <Building2 className="w-4 h-4 text-gray-400" />
                  )}
                  <div className="flex items-center gap-1.5 min-w-0">
                    {job.company_url ? (
                      <a href={job.company_url} target="_blank" rel="noopener noreferrer"
                        className="text-gray-700 text-sm font-medium line-clamp-1 hover:text-blue-600 transition">{job.company}</a>
                    ) : (
                      <p className="text-gray-700 text-sm font-medium line-clamp-1">{job.company}</p>
                    )}
                    {job.company_rating && (
                      <span className="flex items-center text-xs text-yellow-600 shrink-0">
                        <Star className="w-3 h-3 mr-0.5 fill-yellow-400 text-yellow-400" />{job.company_rating.toFixed(1)}
                      </span>
                    )}
                  </div>
                </div>
                <div className="space-y-1.5 text-xs text-gray-500 mb-3 flex-1">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center">
                      <MapPin className="w-3.5 h-3.5 mr-1 shrink-0 text-gray-400" />{job.city}{job.location_full && job.location_full !== job.city ? <span className="text-gray-400 ml-1 truncate max-w-[140px]" title={job.location_full}>({job.location_full.replace(/,\s*India$/i, '').replace(new RegExp(job.city, 'i'), '').replace(/^[,\s]+/, '').trim() || job.location_full})</span> : ''}
                    </span>
                    {job.domain && job.domain !== 'General' && (
                      <span className="flex items-center">{DOMAIN_ICONS[job.domain] || '\u{1F4C1}'} {job.domain}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="flex items-center">
                      <GraduationCap className="w-3.5 h-3.5 mr-1 shrink-0 text-gray-400" />{job.experience_range || 'Fresher'}
                    </span>
                    {job.job_type && <span className="text-gray-400">{'\u00B7'} {job.job_type}</span>}
                  </div>
                  {formatSalary(job) && (
                    <div className="flex items-center text-green-700 font-semibold text-xs">
                      <IndianRupee className="w-3 h-3 mr-1" />{formatSalary(job)}
                      {job.salary_period && <span className="font-normal text-gray-400 ml-1">/{job.salary_period}</span>}
                    </div>
                  )}
                </div>
                {job.technology && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {job.technology.split(',').slice(0, 5).map((tech: string, i: number) => (
                      <span key={i} className="bg-blue-50 text-blue-700 text-[10px] px-2 py-0.5 rounded-md font-medium border border-blue-100">{tech.trim()}</span>
                    ))}
                    {job.technology.split(',').length > 5 && (
                      <span className="text-[10px] text-gray-400 px-1">+{job.technology.split(',').length - 5}</span>
                    )}
                  </div>
                )}
                {job.skills && !job.technology && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {job.skills.split(',').slice(0, 4).map((skill: string, i: number) => (
                      <span key={i} className="bg-gray-50 text-gray-600 text-[10px] px-2 py-0.5 rounded-md border border-gray-100">{skill.trim()}</span>
                    ))}
                  </div>
                )}
                {job.description && (
                  <div className="mb-3">
                    <p className={`text-xs text-gray-500 leading-relaxed ${expandedJob === job.id ? '' : 'line-clamp-2'}`}>{job.description}</p>
                    <button onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                      className="text-[11px] text-blue-600 mt-1 flex items-center gap-0.5 hover:underline">
                      {expandedJob === job.id ? (<><ChevronUp className="w-3 h-3" /> Less</>) : (<><ChevronDown className="w-3 h-3" /> More</>)}
                    </button>
                  </div>
                )}
                <div className="flex justify-between items-center mt-auto pt-3 border-t border-gray-100">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${SOURCE_COLORS[job.source] || 'bg-gray-100 text-gray-600 border-gray-200'}`}>{job.source}</span>
                    <span className="text-[10px] text-gray-400 flex items-center gap-0.5">
                      <Clock className="w-3 h-3" />{timeAgo(job.date_posted || job.posted_date)}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {job.job_url_direct && (
                      <a href={job.job_url_direct} target="_blank" rel="noopener noreferrer"
                        className="bg-green-600 text-white text-xs px-3 py-1 rounded-md font-medium hover:bg-green-700 transition">Apply</a>
                    )}
                    <a href={job.url} target="_blank" rel="noopener noreferrer"
                      className="text-blue-600 text-xs font-medium hover:underline flex items-center gap-0.5 px-2 py-1 rounded-md hover:bg-blue-50 transition">
                      View <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {displayJobs.length === 0 && !loading && (
            <div className="text-center py-20">
              {showBookmarksOnly ? (
                <>
                  <Bookmark className="w-14 h-14 mx-auto text-gray-200 mb-4" />
                  <p className="text-gray-500 text-lg mb-2">No saved jobs yet</p>
                  <p className="text-gray-400 text-sm mb-4">Click the bookmark icon on any job to save it here.</p>
                  <button onClick={() => setShowBookmarksOnly(false)} className="text-blue-600 text-sm hover:underline">Browse all jobs</button>
                </>
              ) : (
                <>
                  <Search className="w-14 h-14 mx-auto text-gray-200 mb-4" />
                  <p className="text-gray-500 text-lg mb-2">No jobs found</p>
                  <p className="text-gray-400 text-sm mb-4">Try adjusting your filters or click &quot;Refresh&quot; to fetch fresh data.</p>
                  <div className="flex gap-3 justify-center">
                    <button onClick={() => { resetFilters(); setTimeout(fetchJobs, 100); }}
                      className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm hover:bg-gray-50">Clear Filters</button>
                    <button onClick={triggerScrape}
                      className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium">Refresh</button>
                  </div>
                </>
              )}
            </div>
          )}

          {hasMore && !showBookmarksOnly && displayJobs.length > 0 && (
            <div className="text-center mt-8">
              <button onClick={loadMore} disabled={loadingMore}
                className="border border-gray-300 text-gray-700 px-8 py-2.5 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50 font-medium transition inline-flex items-center gap-2">
                {loadingMore ? (<><RefreshCw className="w-4 h-4 animate-spin" /> Loading...</>) : (<>Load More {'\u00B7'} {totalJobs - jobs.length} remaining</>)}
              </button>
            </div>
          )}
        </>
      )}
    </main>
  );
}
