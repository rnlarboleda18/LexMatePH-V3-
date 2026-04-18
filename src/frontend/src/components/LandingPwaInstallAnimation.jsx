import React from 'react';
import { MonitorDown, MoreVertical, Smartphone, SquareArrowUp } from 'lucide-react';

/** Same asset as manifest / tab icons (`public/pwa-192x192.png`). */
const PWA_ICON_SRC = '/pwa-192x192.png';

const LOOP_S = 20;

/** Domain text shown in demo address bars (matches production marketing URL). */
const MOCK_URL_IN_BAR = 'www.lexmateph.com';
const MOCK_URL_IN_BAR_HTTPS = 'https://www.lexmateph.com';

/** Official mark for in-demo “app icon” slots (gradient + Scale from build script). */
function OfficialAppIcon({ className = 'h-8 w-8', rounded = 'rounded-lg' }) {
    return (
        <img
            src={PWA_ICON_SRC}
            alt=""
            width={64}
            height={64}
            className={`${rounded} object-cover shadow-sm ${className}`}
            decoding="async"
            aria-hidden="true"
        />
    );
}

function ChromePwaInstallIcon({ className }) {
    return <MonitorDown className={className} strokeWidth={2} aria-hidden />;
}

function IosShareIcon({ className }) {
    return <SquareArrowUp className={className} strokeWidth={2.25} aria-hidden />;
}

function PlaceholderAppIcon({ label, compact }) {
    return (
        <div
            className={`flex aspect-square w-full flex-col items-center justify-center rounded-lg bg-white/10 shadow-inner ring-1 ring-white/10 ${
                compact ? 'max-w-[1.45rem]' : 'max-w-[2.5rem]'
            }`}
            aria-hidden
        >
            <span className={`font-bold text-white/50 ${compact ? 'text-[7px]' : 'text-[9px]'}`}>{label}</span>
        </div>
    );
}

/** Final loop segment (≈80–100%): home grid with pulsing official icon, inside phone/tablet screens only. */
function InDeviceHomeScreenGrid({ variant, compact }) {
    const phone = variant === 'phone';
    const ph = compact;
    const lbl = ph ? 'text-[5px]' : 'text-[6px]';
    const icoLm = ph ? 'h-7 w-7' : 'h-9 w-9';
    const icoPl = ph ? 'h-11 w-11' : 'h-10 w-10';
    const rnd = ph ? 'rounded-md' : 'rounded-xl';
    return (
        <div className="landing-pwa-home-screen pointer-events-none absolute inset-0 z-30 overflow-hidden" aria-hidden>
            <div
                className={`flex h-full w-full flex-col bg-gradient-to-b from-slate-700 via-slate-800 to-slate-900 shadow-inner ring-1 ring-black/15 ${ph ? 'p-1.5' : 'p-2'}`}
            >
                {phone ? (
                    <div
                        className={`grid flex-1 grid-cols-2 grid-rows-2 place-items-center ${ph ? 'gap-0.5 px-0.5 pt-0.5' : 'gap-1.5 px-1 pt-1'}`}
                    >
                        <div className={`flex flex-col items-center ${ph ? 'gap-0.5' : 'gap-1'}`}>
                            <PlaceholderAppIcon label="A" compact={ph} />
                            <span className={`max-w-full truncate text-center ${lbl} text-white/45`}>App</span>
                        </div>
                        <div className={`flex flex-col items-center ${ph ? 'gap-0.5' : 'gap-1'}`}>
                            <PlaceholderAppIcon label="B" compact={ph} />
                            <span className={`max-w-full truncate text-center ${lbl} text-white/45`}>App</span>
                        </div>
                        <div className={`flex flex-col items-center ${ph ? 'gap-0.5' : 'gap-1'}`}>
                            <PlaceholderAppIcon label="C" compact={ph} />
                            <span className={`max-w-full truncate text-center ${lbl} text-white/45`}>App</span>
                        </div>
                        <div className={`flex flex-col items-center ${ph ? 'gap-0.5' : 'gap-1'}`}>
                            <div className={`landing-pwa-installed-icon flex items-center justify-center ${ph ? 'rounded-md' : 'rounded-xl'}`}>
                                <OfficialAppIcon className={icoLm} rounded={rnd} />
                            </div>
                            <span className={`max-w-full truncate text-center ${lbl} font-medium text-white/90`}>LexMatePH</span>
                        </div>
                    </div>
                ) : (
                    <div
                        className={`grid flex-1 grid-cols-4 place-items-start ${ph ? 'gap-0.5 px-0.5 pt-1' : 'gap-2 px-1.5 pt-2'}`}
                    >
                        <div className={`flex flex-col items-center ${ph ? 'gap-0.5' : 'gap-1'}`}>
                            <PlaceholderAppIcon label="A" compact={ph} />
                            <span className={`w-full truncate text-center ${lbl} text-white/45`}>App</span>
                        </div>
                        <div className={`flex flex-col items-center ${ph ? 'gap-0.5' : 'gap-1'}`}>
                            <PlaceholderAppIcon label="B" compact={ph} />
                            <span className={`w-full truncate text-center ${lbl} text-white/45`}>App</span>
                        </div>
                        <div className={`flex flex-col items-center ${ph ? 'gap-0.5' : 'gap-1'}`}>
                            <div className={`landing-pwa-installed-icon flex items-center justify-center ${ph ? 'rounded-md' : 'rounded-xl'}`}>
                                <OfficialAppIcon className={icoPl} rounded={rnd} />
                            </div>
                            <span className={`w-full truncate text-center ${lbl} font-medium text-white/90`}>LexMatePH</span>
                        </div>
                        <div className={`flex flex-col items-center ${ph ? 'gap-0.5' : 'gap-1'}`}>
                            <PlaceholderAppIcon label="C" compact={ph} />
                            <span className={`w-full truncate text-center ${lbl} text-white/45`}>App</span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

/**
 * @param {{ compact?: boolean }} props — `compact`: hero tile (narrow column); default: full #install section
 */
function LandingPwaInstallAnimation({ compact = false }) {
    const cap = 'text-xs sm:text-sm';
    const capTray = 'min-h-[5rem] sm:min-h-[4.5rem] mt-5 px-2';

    const fig = (isCompact) =>
        `mb-1 font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 ${isCompact ? 'text-[8px] sm:text-[9px]' : 'mb-2 text-[10px]'}`;

    return (
        <div
            className={`landing-pwa-install-anim mx-auto w-full ${compact ? 'landing-pwa-install-anim--compact mt-0 max-w-full' : 'mt-6 max-w-3xl'}`}
            role="img"
            aria-label={`Animated loop (${LOOP_S} seconds): open LexMatePH, use Share or install in the address bar, add to Home Screen or install, enable Open as Web App on iOS, then see LexMatePH with the official icon on the Home Screen inside each device preview.`}
        >
            {compact ? (
                <div className="flex w-full min-w-0 flex-col">
                    <div className="flex flex-row items-end justify-center gap-3 sm:gap-4 lg:gap-5">
                        <figure className="flex min-w-0 shrink-0 flex-col items-center">
                            <figcaption className={fig(true)}>Phone (iOS)</figcaption>
                            <PhoneMock compact />
                        </figure>
                        <div className="flex min-w-0 flex-1 flex-col items-center gap-2 sm:gap-3">
                            <p className="mb-0.5 flex w-full items-center justify-center gap-2 text-center text-sm font-medium leading-snug text-gray-800 dark:text-gray-100 sm:mb-1 sm:gap-2.5 sm:text-base">
                                <Smartphone
                                    className="h-4 w-4 shrink-0 text-indigo-600 dark:text-indigo-400 sm:h-5 sm:w-5"
                                    strokeWidth={2}
                                    aria-hidden
                                />
                                <span className="min-w-0">
                                    Browser or installed PWA — same LexMatePH experience.
                                </span>
                            </p>
                            <DesktopChromeMock compact />
                            <figure className="flex w-full min-w-0 flex-col items-center">
                                <figcaption className={fig(true)}>Tablet (Android)</figcaption>
                                <div className="flex w-full justify-center">
                                    <TabletMock compact />
                                </div>
                            </figure>
                        </div>
                    </div>
                </div>
            ) : (
                <>
                    <div className="flex flex-col items-stretch justify-center gap-8 sm:flex-row sm:items-end sm:justify-center sm:gap-10">
                        <figure className="flex flex-col items-center">
                            <figcaption className={fig(false)}>Phone (iOS)</figcaption>
                            <PhoneMock compact={false} />
                        </figure>
                        <figure className="flex flex-col items-center">
                            <figcaption className={fig(false)}>Tablet (Android)</figcaption>
                            <TabletMock compact={false} />
                        </figure>
                    </div>

                    <DesktopChromeMock compact={false} />

                    <div
                        className={`landing-pwa-caption-tray relative mx-auto max-w-lg text-center font-medium text-gray-600 dark:text-gray-400 ${cap} ${capTray}`}
                    >
                        <p className="landing-pwa-caption landing-pwa-caption-1 absolute inset-x-0 top-0">
                            ① Open LexMatePH in Safari
                        </p>
                        <p className="landing-pwa-caption landing-pwa-caption-2 absolute inset-x-0 top-0">
                            ② Tap Share in the address bar (arrow-up icon)
                        </p>
                        <p className="landing-pwa-caption landing-pwa-caption-3 absolute inset-x-0 top-0">
                            ③ Choose Add to Home Screen — or Install in Chrome (icon in the address bar)
                        </p>
                        <p className="landing-pwa-caption landing-pwa-caption-4 absolute inset-x-0 top-0">
                            ④ Turn on Open as Web App, then open LexMatePH from your Home Screen
                        </p>
                        <p className="landing-pwa-caption landing-pwa-caption-5 absolute inset-x-0 top-0">
                            ⑤ LexMatePH appears with your official icon alongside your other apps
                        </p>
                    </div>
                </>
            )}
        </div>
    );
}

function PhoneMock({ compact }) {
    const outer = compact ? 'w-[182px]' : 'w-[142px]';
    const innerH = compact ? 'h-[388px]' : 'h-[288px]';
    const round = compact ? 'rounded-[1.5rem] border-2' : 'rounded-[1.65rem] border-[3px]';
    const innerRound = compact ? 'rounded-[1.2rem]' : 'rounded-[1.35rem]';
    const barPad = compact ? 'px-2 py-1.5' : 'px-2 py-1.5';
    const barH = compact ? 'h-10' : 'h-9';
    const urlText = compact ? 'text-[14px]' : 'text-[13px]';
    const shareBox = compact ? 'h-7 w-7' : 'h-7 w-7';
    const shareIco = compact ? 'h-4 w-4' : 'h-4 w-4';
    const logoBox = compact ? 'h-9 w-9 mb-1' : 'h-9 w-9 mb-2';
    const p = compact ? 'p-2' : 'p-2';
    const bottomBar = compact ? 'h-8 px-2' : 'h-8 px-4';

    return (
        <div className={`${outer} shrink-0`}>
            <div className={`${round} border-slate-700 bg-slate-800 p-[2px] shadow-xl ring-1 ring-black/20 dark:border-slate-600`}>
                <div className={`flex ${innerH} flex-col overflow-hidden ${innerRound} bg-white dark:bg-zinc-950`}>
                    <div className={`flex shrink-0 items-center justify-center bg-slate-100 pt-0.5 dark:bg-zinc-900 ${compact ? 'h-7' : 'h-5'}`}>
                        <div className={`rounded-full bg-slate-300/90 dark:bg-zinc-700 ${compact ? 'h-0.5 w-11' : 'h-0.5 w-8'}`} />
                    </div>
                    <div className={`shrink-0 border-b border-slate-200/90 bg-[#e8e8ed] dark:border-zinc-800 dark:bg-zinc-900 ${barPad}`}>
                        <div
                            className={`flex ${barH} w-full items-center gap-1 rounded-md bg-white px-1.5 shadow-sm ring-1 ring-black/[0.06] dark:bg-zinc-800 dark:ring-white/10`}
                        >
                            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500/90" aria-hidden />
                            <span
                                className={`min-w-0 flex-1 truncate text-center font-medium tabular-nums text-gray-800 dark:text-gray-100 ${urlText}`}
                            >
                                {MOCK_URL_IN_BAR}
                            </span>
                            <div
                                className={`landing-pwa-share-ios flex shrink-0 items-center justify-center rounded text-blue-600 dark:text-blue-400 ${shareBox}`}
                            >
                                <IosShareIcon className={shareIco} />
                            </div>
                        </div>
                    </div>
                    <div className="relative min-h-0 flex-1 bg-gradient-to-b from-violet-100/90 to-indigo-50 dark:from-violet-950/40 dark:to-indigo-950/30">
                        <div className="landing-pwa-content-glow pointer-events-none absolute inset-0 opacity-80" aria-hidden />
                        <div className={`relative ${p}`}>
                            <div className={`mx-auto flex items-center justify-center overflow-hidden rounded-lg shadow-md ring-1 ring-black/10 ${logoBox}`}>
                                <OfficialAppIcon className="h-9 w-9" rounded={compact ? 'rounded-lg' : 'rounded-xl'} />
                            </div>
                            <div className="mx-auto h-1 w-4/5 rounded bg-white/50 dark:bg-white/10" />
                            <div className="mx-auto mt-0.5 h-1 w-3/5 rounded bg-white/35 dark:bg-white/5" />
                        </div>
                        <div className="landing-pwa-ios-sheet-add pointer-events-none absolute inset-x-0 bottom-0 z-10 rounded-t-lg border border-slate-200/80 bg-white/98 shadow-lg dark:border-zinc-700 dark:bg-zinc-900/98">
                            <div
                                className={`border-b border-slate-100 px-2 py-1 text-center font-semibold text-slate-400 dark:border-zinc-800 dark:text-zinc-500 ${compact ? 'text-[7px]' : 'text-[9px]'}`}
                            >
                                Add to Home Screen
                            </div>
                            <div className={`flex items-center gap-1 ${compact ? 'px-2 py-1.5' : 'gap-2 px-3 py-2.5'}`}>
                                <div className={`shrink-0 overflow-hidden rounded-md shadow-sm ring-1 ring-black/10 ${compact ? 'h-7 w-7' : 'h-9 w-9'}`}>
                                    <OfficialAppIcon className={compact ? 'h-7 w-7' : 'h-9 w-9'} rounded="rounded-md" />
                                </div>
                                <div className="min-w-0 flex-1 text-left">
                                    <div
                                        className={`truncate font-semibold text-slate-800 dark:text-slate-100 ${compact ? 'text-[8px]' : 'text-[10px]'}`}
                                    >
                                        LexMatePH
                                    </div>
                                    <div className={`text-slate-500 dark:text-zinc-400 ${compact ? 'text-[6px]' : 'text-[8px]'}`}>Add to Home Screen</div>
                                </div>
                                <span
                                    className={`shrink-0 rounded bg-indigo-600 font-bold text-white ${compact ? 'px-1.5 py-0.5 text-[7px]' : 'px-2 py-1 text-[8px]'}`}
                                >
                                    Add
                                </span>
                            </div>
                        </div>
                        <div className="landing-pwa-ios-sheet-webapp pointer-events-none absolute inset-x-0 bottom-0 z-20 rounded-t-lg border border-slate-200/80 bg-white/98 shadow-xl dark:border-zinc-700 dark:bg-zinc-900/98">
                            <div
                                className={`px-2 pb-0.5 pt-1.5 text-center font-semibold text-slate-900 dark:text-white ${compact ? 'text-[8px]' : 'text-[10px]'}`}
                            >
                                LexMatePH
                            </div>
                            <div className={`border-t border-slate-100 dark:border-zinc-800 ${compact ? 'px-2 py-1.5' : 'px-3 py-2.5'}`}>
                                <div className="flex items-center justify-between gap-1">
                                    <span
                                        className={`font-medium leading-tight text-slate-700 dark:text-zinc-200 ${compact ? 'text-[7px]' : 'text-[9px]'}`}
                                    >
                                        Open as Web App
                                    </span>
                                    <div
                                        className={`relative shrink-0 rounded-full bg-emerald-500 shadow-inner ${compact ? 'h-5 w-8' : 'h-5 w-9'}`}
                                        aria-hidden
                                    >
                                        <div
                                            className={`absolute rounded-full bg-white shadow-sm ${compact ? 'right-0.5 top-0.5 h-3.5 w-3.5' : 'right-0.5 top-0.5 h-4 w-4'}`}
                                        />
                                    </div>
                                </div>
                                <p className={`mt-1 leading-snug text-slate-500 dark:text-zinc-500 ${compact ? 'text-[6px]' : 'mt-1.5 text-[7px]'}`}>
                                    Runs like an app from the Home Screen
                                </p>
                            </div>
                        </div>
                        <InDeviceHomeScreenGrid variant="phone" compact={compact} />
                    </div>
                    <div
                        className={`flex shrink-0 items-center justify-between border-t border-slate-200/90 bg-white/95 dark:border-zinc-800 dark:bg-zinc-950 ${bottomBar}`}
                    >
                        <div className="h-2.5 w-2.5 rounded-sm bg-slate-300/90 dark:bg-zinc-700" aria-hidden />
                        <div className="h-0.5 w-8 rounded-full bg-slate-300/80 dark:bg-zinc-700" aria-hidden />
                        <div className="h-2.5 w-2.5 rounded-sm bg-slate-300/90 dark:bg-zinc-700" aria-hidden />
                    </div>
                </div>
            </div>
        </div>
    );
}

function TabletMock({ compact }) {
    // Compact (landing hero): match width of DesktopChromeMock address bar in the same column (`w-full`).
    const w = compact ? 'w-full' : 'w-[228px]';
    const h = compact ? 'h-[304px]' : 'h-[188px]';
    const border = compact ? 'border-4' : 'border-[6px]';
    const omni = compact
        ? 'min-h-[52px] gap-2 px-3.5 py-2 text-[15px]'
        : 'h-10 gap-1 px-2 py-1 text-[13px]';
    const ico = compact ? 'h-9 w-9' : 'h-7 w-7';
    const mv = compact ? 'h-[18px] w-[18px]' : 'h-3.5 w-3.5';
    const md = compact ? 'h-9 w-9' : 'h-7 w-7';
    const pIco = compact ? 'p-3.5' : 'p-3';
    const logo = compact ? 'h-14 w-14 mb-1' : 'h-10 w-10 mb-2';
    const sheet = compact ? 'right-3 top-16 w-[12rem]' : 'right-2 top-10 w-[9.5rem]';

    return (
        <div className={`${w} shrink-0`}>
            <div className={`rounded-lg ${border} border-slate-700 bg-slate-800 p-0.5 shadow-xl ring-1 ring-black/20 dark:border-slate-600`}>
                <div className={`flex ${h} flex-col overflow-hidden rounded-sm bg-[#35363a] dark:bg-[#35363a]`}>
                    <div className="shrink-0 px-1 pb-0.5 pt-1">
                        <div
                            className={`flex w-full min-w-0 items-center rounded-full bg-[#202124] ring-1 ring-black/35 ${omni}`}
                        >
                            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400/90" aria-hidden />
                            <span className="min-w-0 flex-1 truncate pl-0.5 font-medium leading-none tabular-nums text-[#e8eaed]">
                                {MOCK_URL_IN_BAR}
                            </span>
                            <div className="flex shrink-0 items-center gap-0.5 border-l border-white/10 pl-0.5">
                                <span className={`flex items-center justify-center text-[#9aa0a6] ${ico}`} aria-hidden>
                                    <MoreVertical className={mv} strokeWidth={2.25} />
                                </span>
                                <div className={`landing-pwa-chrome-install flex items-center justify-center rounded text-[#bdc1c6] ${md}`}>
                                    <ChromePwaInstallIcon className={compact ? 'h-5 w-5' : 'h-3.5 w-3.5'} />
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="relative min-h-0 flex-1 overflow-hidden bg-white dark:bg-zinc-950">
                        <div className="relative h-full bg-gradient-to-br from-violet-50 to-indigo-100 dark:from-violet-950/35 dark:to-indigo-950/25">
                            <div className="landing-pwa-content-glow pointer-events-none absolute inset-0 opacity-70" aria-hidden />
                            <div className={`relative ${pIco}`}>
                                <div className={`mx-auto overflow-hidden rounded-lg shadow ring-1 ring-black/10 ${logo}`}>
                                    <OfficialAppIcon className={compact ? 'h-14 w-14' : 'h-10 w-10'} rounded="rounded-lg" />
                                </div>
                                <div className="mx-auto h-1 w-3/4 rounded bg-white/60 dark:bg-white/10" />
                            </div>
                            <div
                                className={`landing-pwa-sheet-android pointer-events-none absolute z-10 overflow-hidden rounded border border-slate-200 bg-white shadow-xl dark:border-zinc-600 dark:bg-zinc-900 ${sheet}`}
                            >
                                <div className="px-2 py-1 text-[9px] font-semibold text-slate-500 dark:text-zinc-400">
                                    Chrome menu
                                </div>
                                <div className={`flex items-center gap-1 border-t border-slate-100 px-2 py-1 dark:border-zinc-800 ${compact ? 'gap-2 py-2.5 px-3' : 'gap-2 px-3 py-2'}`}>
                                    <div className={`shrink-0 overflow-hidden rounded-md ring-1 ring-black/10 ${compact ? 'h-8 w-8' : 'h-7 w-7'}`}>
                                        <OfficialAppIcon className={compact ? 'h-8 w-8' : 'h-7 w-7'} rounded="rounded-md" />
                                    </div>
                                    <span className={`font-semibold text-slate-800 dark:text-slate-100 ${compact ? 'text-[10px]' : 'text-[10px]'}`}>Install app</span>
                                </div>
                            </div>
                            <InDeviceHomeScreenGrid variant="tablet" compact={compact} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function DesktopChromeMock({ compact }) {
    if (compact) {
        return (
            <div className="w-full min-w-0 self-stretch">
                <p className="mb-1 text-center text-[8px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 sm:text-[9px]">
                    Desktop
                </p>
                <div className="overflow-hidden rounded-lg border border-slate-300 bg-[#35363a] shadow-md ring-1 ring-black/15 dark:border-slate-600">
                    <div className="flex h-12 items-center px-2 py-1">
                        <div className="flex h-10 w-full min-w-0 items-center gap-1.5 rounded-md bg-[#202124] px-2 py-1 ring-1 ring-black/25">
                            <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-400/90" aria-hidden />
                            <span className="min-w-0 flex-1 truncate text-left text-[14px] font-medium tabular-nums text-[#e8eaed] sm:text-[15px]">
                                {MOCK_URL_IN_BAR}
                            </span>
                            <div className="landing-pwa-chrome-install flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[#bdc1c6]">
                                <ChromePwaInstallIcon className="h-4 w-4" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
    return (
        <div className="mx-auto mt-8 w-full max-w-lg px-1">
            <p className="mb-2 text-center text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                Desktop (Chrome / Edge)
            </p>
            <div className="overflow-hidden rounded-lg border border-slate-300 bg-[#35363a] shadow-lg ring-1 ring-black/15 dark:border-slate-600">
                <div className="flex h-[3.25rem] items-center px-2.5 py-1.5">
                    <div className="flex h-11 w-full min-w-0 items-center gap-2 rounded-lg bg-[#202124] px-2.5 py-2 ring-1 ring-black/25">
                        <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-400/90" aria-hidden />
                        <span className="min-w-0 flex-1 truncate text-left text-[15px] font-medium tabular-nums text-[#e8eaed] sm:text-[16px]">
                            {MOCK_URL_IN_BAR_HTTPS}
                        </span>
                        <div className="landing-pwa-chrome-install flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[#bdc1c6]">
                            <ChromePwaInstallIcon className="h-[18px] w-[18px]" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default LandingPwaInstallAnimation;
