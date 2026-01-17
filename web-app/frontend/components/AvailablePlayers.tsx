import { useState, useMemo } from "react";
import { Player } from "@/types";
import { PlayerCard } from "./PlayerCard";
import { Search, Filter, Warehouse } from "lucide-react";

interface AvailablePlayersProps {
    players: Player[];
    onDraftPlayer: (player: Player) => void;
    canDraft: boolean;
}

export function AvailablePlayers({ players, onDraftPlayer, canDraft }: AvailablePlayersProps) {
    const [search, setSearch] = useState("");
    const [posFilter, setPosFilter] = useState("All");
    const [teamFilter, setTeamFilter] = useState("All");

    // Extract unique teams for filter dropdown
    const availableTeams = useMemo(() => {
        const teams = new Set(players.map(p => p.Team));
        return ["All", ...Array.from(teams).sort()];
    }, [players]);

    const filtered = useMemo(() => {
        let res = players;

        // 1. Filter
        res = res.filter(p => {
            const matchesSearch = p.Nome.toLowerCase().includes(search.toLowerCase());
            const matchesPos = posFilter === "All" || p['Posição'] === posFilter;
            const matchesTeam = teamFilter === "All" || p.Team === teamFilter;
            return matchesSearch && matchesPos && matchesTeam;
        });

        // 2. Sort by Market Value (Descending)
        res.sort((a, b) => (b['Valor de Mercado'] || 0) - (a['Valor de Mercado'] || 0));

        return res;
    }, [players, search, posFilter, teamFilter]);

    return (
        <div className="flex flex-col h-full bg-[#111] border-l border-white/10">
            {/* Header / Filters */}
            <div className="p-4 border-b border-white/10 space-y-4 bg-[#18181b]">
                <div className="flex items-center gap-2 mb-2">
                    <h2 className="text-xl font-oswald font-bold uppercase text-white tracking-wide">Mercado</h2>
                    <span className="text-xs bg-[#39ff14]/20 text-[#39ff14] px-2 py-0.5 rounded font-bold border border-[#39ff14]/30">
                        {filtered.length}
                    </span>
                </div>

                {/* Search */}
                <div className="relative group">
                    <Search className={`absolute left-3 top-2.5 transition-colors ${search ? 'text-[#39ff14]' : 'text-gray-400 group-hover:text-white'}`} size={16} />
                    <input
                        type="text"
                        placeholder="Buscar jogador..."
                        className={`w-full bg-black/60 border rounded-lg pl-10 pr-4 py-3 text-sm font-bold outline-none transition-all placeholder-gray-500
                        ${search
                                ? "border-[#39ff14] text-white shadow-[0_0_10px_rgba(57,255,20,0.1)]"
                                : "border-white/20 text-white hover:border-white/40 focus:border-[#39ff14]"
                            }`}
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>

                {/* Real Team Filter */}
                <div className="relative group">
                    <Warehouse className={`absolute left-3 top-2.5 transition-colors ${teamFilter !== 'All' ? 'text-black z-10' : 'text-gray-400 group-hover:text-white'}`} size={16} />
                    <select
                        className={`w-full border rounded-lg pl-10 pr-4 py-3 text-sm font-bold outline-none appearance-none cursor-pointer transition-all
                        ${teamFilter !== 'All'
                                ? "bg-[#39ff14] border-[#39ff14] text-black shadow-[0_0_15px_rgba(57,255,20,0.4)]"
                                : "bg-black/60 border-white/20 text-white hover:border-white/40 focus:border-[#39ff14]"
                            }`}
                        value={teamFilter}
                        onChange={(e) => setTeamFilter(e.target.value)}
                    >
                        <option value="All" className="bg-[#18181b] text-white">Todos os Clubes</option>
                        {availableTeams.filter(t => t !== "All").map(t => (
                            <option key={t} value={t} className="bg-[#18181b] text-white">{t}</option>
                        ))}
                    </select>
                </div>

                {/* Position Segmented Control */}
                <div className="bg-black/80 p-1.5 rounded-xl flex border border-white/10 shadow-inner gap-1">
                    {["All", "Forward", "Midfielder", "Defender", "Goalkeeper"].map(pos => {
                        const isActive = posFilter === pos;
                        const labelMap: any = {
                            "All": "TODOS", "Forward": "ATA", "Midfielder": "MEI",
                            "Defender": "DEF", "Goalkeeper": "GOL"
                        };
                        return (
                            <button
                                key={pos}
                                onClick={() => setPosFilter(pos)}
                                className={`flex-1 py-2 text-[10px] font-black uppercase rounded-lg transition-all transform duration-200 ${isActive
                                        ? "bg-[#39ff14] text-black shadow-[0_0_15px_rgba(57,255,20,0.5)] scale-105 z-10"
                                        : "text-gray-500 hover:text-white hover:bg-white/5"
                                    }`}
                            >
                                {labelMap[pos] || pos}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Compact List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar">
                {filtered.slice(0, 100).map((player, idx) => (
                    <PlayerCard
                        key={`${player.Nome}-${player.Team}-${idx}`}
                        player={player}
                        compact={true} // Use compact mode
                        onSelect={() => canDraft && onDraftPlayer(player)}
                    />
                ))}
            </div>
        </div>
    );
}
