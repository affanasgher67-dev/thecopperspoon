"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.apiQueryAvailability = exports.queryAvailability = void 0;
const functions = __importStar(require("firebase-functions/v2"));
const admin = __importStar(require("firebase-admin"));
const core_1 = require("@genkit-ai/core");
const ai_1 = require("@genkit-ai/ai");
const firebase_1 = require("@genkit-ai/firebase");
const googleai_1 = require("@genkit-ai/googleai");
const zod_1 = require("zod");
// Initialize Firebase Admin
admin.initializeApp();
// Configure Genkit
(0, core_1.configureGenkit)({
    plugins: [
        (0, firebase_1.firebase)(),
        (0, googleai_1.googleAI)(), // Requires GOOGLE_GENAI_API_KEY if used for generation, but we'll use it for tooling
    ],
    logLevel: 'debug',
    enableTracingAndMetrics: true,
});
/**
 * Tool: Query Table Availability
 * Connects to Firestore to check occupancy for a specific slot.
 */
exports.queryAvailability = (0, ai_1.defineTool)({
    name: 'queryAvailability',
    description: 'Queries the live database for table availability at a specific date and time.',
    inputSchema: zod_1.z.object({
        date: zod_1.z.string().describe('The reservation date in YYYY-MM-DD format.'),
        time: zod_1.z.string().describe('The reservation time in HH:MM format.'),
    }),
    outputSchema: zod_1.z.object({
        available_seats: zod_1.z.number(),
        booked_seats: zod_1.z.number(),
        max_seats: zod_1.z.number(),
        is_full: zod_1.z.boolean(),
    }),
}, async ({ date, time }) => {
    const db = admin.firestore();
    const reservationsRef = db.collection('reservations');
    // Default capacity (should match Python backend)
    const MAX_SEATS_PER_SLOT = 40;
    // Query all non-cancelled reservations for this date/time
    const snapshot = await reservationsRef
        .where('reservation_date', '==', date)
        .where('reservation_time', '==', time)
        .where('status', '!=', 'cancelled')
        .get();
    let bookedSeats = 0;
    snapshot.forEach(doc => {
        const data = doc.data();
        bookedSeats += Number(data.party_size || 0);
    });
    const available = Math.max(0, MAX_SEATS_PER_SLOT - bookedSeats);
    return {
        available_seats: available,
        booked_seats: bookedSeats,
        max_seats: MAX_SEATS_PER_SLOT,
        is_full: available <= 0,
    };
});
// Export the tool as a callable function (optional, for direct access)
exports.apiQueryAvailability = functions.https.onCall(async (request) => {
    return await (0, exports.queryAvailability)(request.data);
});
//# sourceMappingURL=index.js.map