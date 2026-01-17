import { Team } from "@/types";
import { PlayerCard } from "./PlayerCard";
import { User, Shield, Target, Footprints } from "lucide-react";

interface RosterViewProps {
    team: Team;
}

export function RosterView({ team }: RosterViewProps) {
    const totalValue = team.players.reduce((acc, p) => acc + (p['Valor de Mercado'] || 0), 0);

    // Counts
    const counts = {
        GOL: team.players.filter(p => p['Posição'] === 'Goalkeeper').length,
        DEF: team.players.filter(p => p['Posição'] === 'Defender').length,
        MEI: team.players.filter(p => p['Posição'] === 'Midfielder').length,
        ATA: team.players.filter(p => p['Posição'] === 'Forward').length,
    };

    return (
        <div className="bg-black/40 rounded-xl border border-white/5 p-6 h-full flex flex-col">
            <div className="flex justify-between items-center mb-6 border-b border-white/10 pb-6">
                <div className="flex items-center gap-4">
                    <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center border-2 border-white/10 overflow-hidden shadow-lg">
                        {team.logo ? (
                            <img src={team.logo} className="w-full h-full object-cover" />
                        ) : (
                            <User size={32} className="text-gray-600" />
                        )}
                    </div>
                    <div>
                        <h2 className="text-3xl font-oswald font-bold text-white">{team.name}</h2>
                        <div className="text-xs text-neon-green uppercase tracking-widest font-bold">Elenco Oficial</div>
                    </div>
                </div>
                <div className="text-right bg-white/5 p-3 rounded-lg border border-white/5">
                    <div className="text-[10px] text-gray-500 uppercase font-bold mb-1">Valor do Plantel</div>
                    <div className="text-2xl font-mono text-white font-bold">€{totalValue.toFixed(1)}M</div>
                </div>
            </div>

            {/* Position Indicators */}
            <div className="flex gap-2 mb-4">
                <div className="flex-1 bg-[#EC4899] p-2 rounded flex items-center justify-between border-l-4 border-white/20">
                    <span className="text-[10px] font-bold text-white uppercase">GOL</span>
                    <span className="text-lg font-bold text-white">{counts.GOL}</span>
                </div>
                <div className="flex-1 bg-[#8E44AD] p-2 rounded flex items-center justify-between border-l-4 border-white/20">
                    <span className="text-[10px] font-bold text-white uppercase">DEF</span>
                    <span className="text-lg font-bold text-white">{counts.DEF}</span>
                </div>
                <div className="flex-1 bg-[#F2994A] p-2 rounded flex items-center justify-between border-l-4 border-white/20">
                    <span className="text-[10px] font-bold text-black uppercase">MEI</span>
                    <span className="text-lg font-bold text-black">{counts.MEI}</span>
                </div>
                <div className="flex-1 bg-[#D90429] p-2 rounded flex items-center justify-between border-l-4 border-white/20">
                    <span className="text-[10px] font-bold text-white uppercase">ATA</span>
                    <span className="text-lg font-bold text-white">{counts.ATA}</span>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                {team.players.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-gray-600 space-y-4">
                        <User size={48} className="text-white/5" />
                        <div className="text-sm italic">Nenhum jogador selecionado ainda</div>
                    </div>
                ) : (
                    team.players.map((p, idx) => (
                        <PlayerCard key={idx} player={p} compact />
                    ))
                )}
            </div>
        </div>
    );
}
