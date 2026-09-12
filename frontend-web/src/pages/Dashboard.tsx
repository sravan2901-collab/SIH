import { useAuth } from "../context/AuthContext";

export function Dashboard() {
  const { role, userId, logout } = useAuth();

  return (
    <div className="min-h-screen bg-[#F4F6F8] text-[#1A1F26] p-8 flex flex-col items-center justify-center">
      <div className="w-full max-w-md bg-white border border-[#D8DEE4] rounded-md overflow-hidden shadow-sm">
        <div className="h-1 bg-[#B8862E]" />
        <div className="p-6">
          <h1 className="text-xl font-semibold text-[#1F3B57] mb-2">Dashboard (Reviewer/Admin)</h1>
          <p className="text-sm text-[#5B6472] mb-4">
            Legal Metrology Packaged Commodities Compliance System
          </p>
          <div className="bg-[#F4F6F8] p-3 rounded border border-[#D8DEE4] text-xs font-mono text-[#1A1F26] mb-6">
            <div>Role: {role}</div>
            <div>User ID: {userId}</div>
          </div>
          <button
            type="button"
            onClick={logout}
            className="w-full py-2 px-4 bg-[#1F3B57] hover:bg-[#16293D] text-white text-sm font-medium rounded transition-colors focus-visible:ring-2 focus-visible:ring-[#1F3B57] focus-visible:outline-none"
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
