"use client";

import { useEffect, useState } from "react";
import { DraftState, Player } from "@/types";
import { api } from "@/lib/api";
import { SetupScreen } from "@/components/SetupScreen";
import { DraftHeader } from "@/components/DraftHeader";
import { AvailablePlayers } from "@/components/AvailablePlayers";
import { RosterView } from "@/components/RosterView";
import { DraftBoard } from "@/components/DraftBoard";
import { PitchView } from "@/components/PitchView";
import { ChevronRight, ChevronLeft, LayoutGrid, Users, User, RotateCcw, Undo2, Download } from "lucide-react";

export default function Home() {
  const [state, setState] = useState<DraftState | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [view, setView] = useState<"roster" | "board">("roster"); // Removed 'pitch'
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(true);
  const [viewTeamIdx, setViewTeamIdx] = useState<number | null>(null);
  const [teamScrollIndex, setTeamScrollIndex] = useState(0);

  const refreshState = async () => {
    try {
      const s = await api.getState();
      setState(s);
      const p = await api.getPlayers();
      setPlayers(p);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    const init = async () => {
      try {
        const root = await api.getSetupState();
        if (root.setup) { await refreshState(); } else { setState(null); }
      } catch (e) { console.error(e); }
      setLoading(false);
    };
    init();
  }, []);

  useEffect(() => {
    if (state && !state.is_finished && viewTeamIdx === null) {
      setViewTeamIdx(state.draft_order[state.current_pick_idx].team_idx);
    }
  }, [state, viewTeamIdx]);

  const handleDraftPlayer = async (player: Player) => {
    if (!state) return;
    try {
      const currentPick = state.draft_order[state.current_pick_idx];
      await api.makePick(currentPick.team_idx, player.Nome);
      await refreshState();
    } catch (e) { alert("Erro ao draftar jogador"); }
  };

  const handleTeamScroll = (direction: 'next' | 'prev') => {
    if (!state) return;
    if (direction === 'next') {
      if (teamScrollIndex + 5 < state.teams.length) {
        setTeamScrollIndex(prev => prev + 1);
      }
    } else {
      if (teamScrollIndex > 0) {
        setTeamScrollIndex(prev => prev - 1);
      }
    }
  }

  const handleReset = async () => {
    if (confirm("TEM CERTEZA? Isso apagará todo o progresso do draft atual e voltará para a configuração inicial.")) {
      try {
        await api.resetDraft();
        window.location.reload(); // Hard reload to clear client state
      } catch (e) {
        alert("Erro ao resetar");
      }
    }
  }

  const handleUndo = async () => {
    if (confirm("Desfazer a última escolha?")) {
      try {
        await api.undoPick();
        await refreshState();
      } catch (e) {
        alert("Erro ao desfazer pick");
      }
    }
  }

  if (loading) return <div className="h-screen flex items-center justify-center text-[#39ff14]">Carregando...</div>;
  if (!state) return <SetupScreen onSetupComplete={refreshState} />;

  if (state.is_finished) {
    return (
      <div className="h-screen bg-black text-white p-8">
        <h1 className="text-4xl font-oswald text-[#39ff14] mb-8">Draft Finalizado!</h1>
        <DraftBoard state={state} />

        <div className="fixed top-6 right-6 flex items-center gap-2 z-[100]">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 bg-red-900/20 hover:bg-red-600 text-white/30 hover:text-white px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all border border-white/5 hover:border-red-500 backdrop-blur-sm"
          >
            <RotateCcw size={14} /> Resetar
          </button>

          <a
            href={api.getExportUrl()}
            target="_blank"
            className="flex items-center gap-2 bg-[#39ff14]/20 hover:bg-[#39ff14]/40 text-[#39ff14] px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all border border-[#39ff14]/20 hover:border-[#39ff14]/50 backdrop-blur-sm"
          >
            <Download size={14} /> Baixar CSV
          </a>
        </div>
      </div >
    );
  }

  const currentPickInfo = state.draft_order[state.current_pick_idx];
  const activeTeam = state.teams[currentPickInfo.team_idx];
  const teamToView = viewTeamIdx !== null ? state.teams[viewTeamIdx] : activeTeam;

  const visibleTeams = state.teams.slice(teamScrollIndex, teamScrollIndex + 5);

  return (
    <main className="h-screen flex flex-col overflow-hidden bg-[#09090b]">
      <DraftHeader
        leagueName={state.league_name}
        round={currentPickInfo.round}
        pick={state.current_pick_idx + 1}
        activeTeamName={activeTeam.name}
        activeTeamLogo={activeTeam.logo}
      />

      <div className="flex-1 flex overflow-hidden relative">
        <div className={`flex-1 flex flex-col p-6 gap-6 overflow-hidden transition-all duration-300 ${isSidebarOpen ? 'mr-[400px]' : ''}`}>

          {/* Header Area */}
          <div className="flex justify-between items-end">
            {/* Tabs */}
            <div className="flex gap-4">
              <button onClick={() => setView("roster")} className={`flex items-center gap-2 px-6 py-2 rounded-lg font-bold uppercase transition-all ${view === "roster" ? "bg-white text-black" : "bg-white/5 text-gray-400 hover:bg-white/10"}`}>
                <Users size={18} /> Elenco
              </button>
              <button onClick={() => setView("board")} className={`flex items-center gap-2 px-6 py-2 rounded-lg font-bold uppercase transition-all ${view === "board" ? "bg-white text-black" : "bg-white/5 text-gray-400 hover:bg-white/10"}`}>
                <LayoutGrid size={18} /> Board Geral
              </button>
            </div>

            {/* Team Carousel Selector - Visible on Roster view */}
            {view === 'roster' && (
              <div className="flex items-center gap-2 bg-black/40 p-2 rounded-lg border border-white/10">
                <button
                  onClick={() => handleTeamScroll('prev')}
                  disabled={teamScrollIndex === 0}
                  className="p-1 hover:text-white text-gray-500 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronLeft size={20} />
                </button>

                <div className="flex gap-2">
                  {visibleTeams.map((t, i) => {
                    const actualIndex = teamScrollIndex + i;
                    return (
                      <button
                        key={t.id}
                        onClick={() => setViewTeamIdx(actualIndex)}
                        className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all relative group
                                                ${viewTeamIdx === actualIndex
                            ? "border-[#39ff14] shadow-[0_0_10px_rgba(57,255,20,0.5)] scale-110 z-10"
                            : "border-transparent bg-white/5 hover:bg-white/10 hover:border-white/20"
                          }`}
                        title={t.name}
                      >
                        {t.logo ? (
                          <img src={t.logo} className="w-full h-full object-cover rounded-full" />
                        ) : (
                          <User size={20} className="text-gray-500" />
                        )}
                        {currentPickInfo.team_idx === actualIndex && (
                          <div className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-red-500 rounded-full border border-black animate-pulse"></div>
                        )}
                      </button>
                    );
                  })}
                </div>

                <button
                  onClick={() => handleTeamScroll('next')}
                  disabled={teamScrollIndex + 5 >= state.teams.length}
                  className="p-1 hover:text-white text-gray-500 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronRight size={20} />
                </button>
              </div>
            )}
          </div>

          <div className="flex-1 overflow-hidden relative">
            {/* Floating Sidebar Toggle */}
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="absolute right-0 top-1/2 -translate-y-1/2 bg-[#39ff14] text-black p-2 rounded-l-md z-50 shadow-[0_0_15px_rgba(57,255,20,0.5)] hover:pl-4 transition-all"
            >
              {isSidebarOpen ? <ChevronRight size={24} /> : <ChevronLeft size={24} />}
            </button>

            {/* Consolidated View: Split Screen */}
            {view === "roster" && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">
                <div className="overflow-hidden">
                  <RosterView team={teamToView} />
                </div>
                <div className="overflow-hidden rounded-xl">
                  <PitchView team={teamToView} />
                </div>
              </div>
            )}

            {view === "board" && <DraftBoard state={state} />}
          </div>
        </div>

        <div
          className={`fixed top-[88px] bottom-0 right-0 w-[400px] bg-[#111] border-l border-white/10 transition-transform duration-300 transform ${isSidebarOpen ? 'translate-x-0' : 'translate-x-full'}`}
        >
          <AvailablePlayers
            players={players}
            onDraftPlayer={handleDraftPlayer}
            canDraft={true}
          />
        </div>
      </div>


      {/* Reset Button (Bottom Left) */}
      {/* Reset Button (Bottom Left) */}
      {/* Action Buttons (Top Right) */}
      <div className="fixed top-6 right-6 flex items-center gap-2 z-[100]">
        {/* Undo Button */}
        <button
          onClick={handleUndo}
          disabled={!state || state.current_pick_idx === 0}
          className="flex items-center gap-2 bg-blue-900/20 hover:bg-blue-600 text-white/30 hover:text-white px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all border border-white/5 hover:border-blue-500 backdrop-blur-sm disabled:opacity-0 disabled:pointer-events-none"
        >
          <Undo2 size={14} /> Desfazer
        </button>

        {/* Reset Button */}
        <button
          onClick={handleReset}
          className="flex items-center gap-2 bg-red-900/20 hover:bg-red-600 text-white/30 hover:text-white px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all border border-white/5 hover:border-red-500 backdrop-blur-sm"
        >
          <RotateCcw size={14} /> Resetar
        </button>
      </div>
    </main >
  );
}
