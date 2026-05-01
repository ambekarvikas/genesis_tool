"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Patient = { id: number; name: string; age: number; gender: string };

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // new-patient form
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("Unknown");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    fetch(`${API}/patients`)
      .then((r) => r.json())
      .then((data) => { setPatients(data); setLoading(false); })
      .catch(() => { setError("Failed to load patients"); setLoading(false); });
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const res = await fetch(`${API}/patients`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), age: parseInt(age) || 0, gender }),
      });
      if (!res.ok) throw new Error(await res.text());
      setName(""); setAge(""); setGender("Unknown");
      load();
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Failed to create patient");
    } finally {
      setCreating(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-4xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Patients</h1>
            <p className="text-gray-400 text-sm mt-1">Manage patients and compare reports</p>
          </div>
          <Link href="/" className="text-sm text-blue-400 hover:text-blue-300">
            ← Back to Analysis
          </Link>
        </div>

        {/* Create patient form */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4 uppercase tracking-wide">
            New Patient
          </h2>
          <form onSubmit={handleCreate} className="flex flex-wrap gap-3 items-end">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-400">Full Name *</label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-52 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Jane Smith"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-400">Age</label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-20 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="40"
                min={0}
                max={120}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-400">Gender</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {["Unknown", "Female", "Male", "Non-binary", "Other"].map((g) => (
                  <option key={g}>{g}</option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={creating}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:text-blue-300 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {creating ? "Creating…" : "Create Patient"}
            </button>
          </form>
          {createError && <p className="text-red-400 text-xs mt-2">{createError}</p>}
        </div>

        {/* Patient list */}
        {loading ? (
          <p className="text-gray-400">Loading…</p>
        ) : error ? (
          <p className="text-red-400">{error}</p>
        ) : patients.length === 0 ? (
          <p className="text-gray-500 text-sm">No patients yet. Create one above.</p>
        ) : (
          <div className="grid gap-3">
            {patients.map((p) => (
              <Link
                key={p.id}
                href={`/patients/${p.id}`}
                className="flex items-center justify-between bg-gray-900 border border-gray-800 hover:border-blue-700 rounded-xl px-5 py-4 transition-colors group"
              >
                <div>
                  <p className="font-medium text-white group-hover:text-blue-300 transition-colors">
                    {p.name}
                  </p>
                  <p className="text-gray-400 text-xs mt-0.5">
                    {p.age > 0 ? `${p.age} y/o` : "Age unknown"} · {p.gender}
                  </p>
                </div>
                <span className="text-xs text-gray-500 group-hover:text-blue-400 transition-colors">
                  View →
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
