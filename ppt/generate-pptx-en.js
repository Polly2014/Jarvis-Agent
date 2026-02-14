/**
 * Jarvis-Agent PPT (English Version) — Gradient BGs + PPTX Generation
 * 
 * Usage: node generate-pptx-en.js
 * Output: jarvis-agent-en.pptx
 */

const pptxgen = require('pptxgenjs');
const path = require('path');
const sharp = require('sharp');
const html2pptx = require('../../.claude/skills/pptx/scripts/html2pptx');

const SLIDES_DIR = path.join(__dirname, 'slides-en');
const OUTPUT = path.join(__dirname, 'jarvis-agent-en.pptx');

// Generate gradient background PNGs (shared with CN version)
async function createGradients() {
    console.log('🎨 Generating gradient backgrounds...\n');

    const titleBg = `<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540">
        <rect width="100%" height="100%" fill="#0F1119"/>
        <defs>
            <radialGradient id="g1" cx="50%" cy="45%" r="60%">
                <stop offset="0%" style="stop-color:#1E1535; stop-opacity:1"/>
                <stop offset="100%" style="stop-color:#0F1119; stop-opacity:1"/>
            </radialGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#g1)"/>
        <circle cx="480" cy="200" r="250" fill="#8B5CF6" opacity="0.04"/>
    </svg>`;
    await sharp(Buffer.from(titleBg)).png().toFile(path.join(SLIDES_DIR, 'title-bg.png'));

    const closingBg = `<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540">
        <rect width="100%" height="100%" fill="#0F1119"/>
        <defs>
            <radialGradient id="g3" cx="50%" cy="50%" r="55%">
                <stop offset="0%" style="stop-color:#0F1F1A; stop-opacity:1"/>
                <stop offset="100%" style="stop-color:#0F1119; stop-opacity:1"/>
            </radialGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#g3)"/>
    </svg>`;
    await sharp(Buffer.from(closingBg)).png().toFile(path.join(SLIDES_DIR, 'closing-bg.png'));

    console.log('   ✅ title-bg.png');
    console.log('   ✅ closing-bg.png\n');
}

async function generatePresentation() {
    await createGradients();

    console.log('🚀 Generating Jarvis-Agent PPT (English)...\n');

    const pptx = new pptxgen();
    pptx.layout = 'LAYOUT_16x9';
    pptx.author = 'Polly Wang';
    pptx.title = 'Jarvis-Agent: A Digimon-Style AI Agent';
    pptx.subject = 'Jarvis-Agent Presentation 2026 (English)';

    const slides = [
        'slide01-title.html',
        'slide02-problem.html',
        'slide03-insight.html',
        'slide04-five-dimensions.html',
        'slide05-phase1.html',
        'slide06-phase2.html',
        'slide07-phase3.html',
        'slide08-phase4.html',
        'slide09-architecture.html',
        'slide10-demo.html',
        'slide11-roadmap.html',
        'slide12-closing.html'
    ];

    for (let i = 0; i < slides.length; i++) {
        const slidePath = path.join(SLIDES_DIR, slides[i]);
        console.log(`📄 [${i + 1}/${slides.length}] ${slides[i]}`);
        try {
            await html2pptx(slidePath, pptx);
        } catch (err) {
            console.error(`   ❌ Error: ${err.message}`);
        }
    }

    await pptx.writeFile({ fileName: OUTPUT });
    console.log(`\n✅ Done! Output: ${OUTPUT}`);
}

generatePresentation().catch(console.error);
