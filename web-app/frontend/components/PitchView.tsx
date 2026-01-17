import { Player, Team } from "@/types";

interface PitchViewProps {
    team: Team;
}

export function PitchView({ team }: PitchViewProps) {
    // Categorize players
    const gks = team.players.filter(p => p['Posição'] === 'Goalkeeper');
    const defs = team.players.filter(p => p['Posição'] === 'Defender');
    const mids = team.players.filter(p => p['Posição'] === 'Midfielder');
    const fwds = team.players.filter(p => p['Posição'] === 'Forward');

    // Counts
    const counts = {
        GOL: gks.length,
        DEF: defs.length,
        MEI: mids.length,
        ATA: fwds.length,
    };

    // Mappers
    const getColor = (pos: string) => {
        switch (pos) {
            case "Forward": return "#D90429"; // Strong Blood Red
            case "Midfielder": return "#F2994A"; // Orange
            case "Defender": return "#8E44AD"; // Purple
            case "Goalkeeper": return "#EC4899"; // Pink
            default: return "#555";
        }
    }

    const getAcronym = (pos: string) => {
        switch (pos) {
            case "Forward": return "ATA";
            case "Midfielder": return "MEI";
            case "Defender": return "DEF";
            case "Goalkeeper": return "GOL";
            default: return pos.substring(0, 3).toUpperCase();
        }
    }

    const renderPlayerDot = (p: Player) => (
        <div key={p.Nome} className="flex flex-col items-center group relative z-10 cursor-pointer m-1">
            {/* Player Dot - Smaller */}
            <div
                className="w-11 h-11 rounded-full border-2 border-white shadow-[0_4px_6px_rgba(0,0,0,0.5)] group-hover:scale-110 transition-transform flex items-center justify-center relative overflow-hidden"
                style={{ backgroundColor: getColor(p['Posição']) }}
            >
                <div className="absolute inset-0 bg-gradient-to-tr from-black/20 to-transparent"></div>
                <span className="text-xs font-black text-white/90 drop-shadow-md z-10">
                    {getAcronym(p['Posição'])}
                </span>
            </div>

            {/* Name Label - Smaller */}
            <div className="mt-1 bg-black/90 px-3 py-1 rounded-full border border-white/20 shadow-lg backdrop-blur-sm">
                <div className="text-[10px] font-black text-white uppercase tracking-wider whitespace-nowrap">
                    {p.Nome}
                </div>
            </div>
        </div>
    );

    return (
        <div className="h-full w-full bg-[#1a4a1c] rounded-xl relative overflow-hidden border border-white/10 shadow-inner flex flex-col justify-between p-2 bg-[url('https://www.transparenttextures.com/patterns/grass.png')]">

            {/* Position Indicators Overlay - Larger */}
            <div className="absolute top-4 right-4 flex flex-col gap-2 z-20">
                <div className="w-12 h-10 bg-[#D90429] rounded flex items-center justify-center text-white font-bold border border-white/20 shadow-sm text-sm">
                    {counts.ATA}
                </div>
                <div className="w-12 h-10 bg-[#F2994A] rounded flex items-center justify-center text-black font-bold border border-white/20 shadow-sm text-sm">
                    {counts.MEI}
                </div>
                <div className="w-12 h-10 bg-[#8E44AD] rounded flex items-center justify-center text-white font-bold border border-white/20 shadow-sm text-sm">
                    {counts.DEF}
                </div>
                <div className="w-12 h-10 bg-[#EC4899] rounded flex items-center justify-center text-white font-bold border border-white/20 shadow-sm text-sm">
                    {counts.GOL}
                </div>
            </div>

            {/* Field Lines overlay */}
            <div className="absolute inset-0 pointer-events-none opacity-50">
                <div className="absolute top-0 left-0 right-0 h-1/2 border-b-2 border-white/30"></div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 rounded-full border-2 border-white/30"></div>
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-24 border-b-2 border-l-2 border-r-2 border-white/30 rounded-b-lg"></div>
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-48 h-24 border-t-2 border-l-2 border-r-2 border-white/30 rounded-t-lg"></div>
                <div className="absolute top-0 left-0 w-full h-full border-[3px] border-white/30 rounded-xl"></div>
            </div>

            {/* Forwards (ATA) - Top */}
            <div className="flex justify-center flex-wrap gap-x-2 gap-y-1 relative z-10 flex-1 content-start pt-4 px-8">
                {fwds.map(renderPlayerDot)}
            </div>

            {/* Midfielders (MEI) */}
            <div className="flex justify-center flex-wrap gap-x-2 gap-y-1 relative z-10 flex-1 content-center px-8">
                {mids.map(renderPlayerDot)}
            </div>

            {/* Defenders (DEF) */}
            <div className="flex justify-center flex-wrap gap-x-2 gap-y-1 relative z-10 flex-1 content-center px-8">
                {defs.map(renderPlayerDot)}
            </div>

            {/* Goalkeepers (GOL) - Bottom */}
            <div className="flex justify-center flex-wrap gap-x-2 gap-y-1 relative z-10 flex-1 content-end pb-4 px-8">
                {gks.map(renderPlayerDot)}
            </div>
        </div>

    );
}
