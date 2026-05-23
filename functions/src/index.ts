import * as functions from 'firebase-functions/v2';
import * as admin from 'firebase-admin';
import { configureGenkit } from '@genkit-ai/core';
import { defineTool } from '@genkit-ai/ai';
import { firebase } from '@genkit-ai/firebase';
import { googleAI } from '@genkit-ai/googleai';
import { z } from 'zod';

// Initialize Firebase Admin
admin.initializeApp();

// Configure Genkit
configureGenkit({
  plugins: [
    firebase(),
    googleAI(), // Requires GOOGLE_GENAI_API_KEY if used for generation, but we'll use it for tooling
  ],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

/**
 * Tool: Query Table Availability
 * Connects to Firestore to check occupancy for a specific slot.
 */
export const queryAvailability = defineTool(
  {
    name: 'queryAvailability',
    description: 'Queries the live database for table availability at a specific date and time.',
    inputSchema: z.object({
      date: z.string().describe('The reservation date in YYYY-MM-DD format.'),
      time: z.string().describe('The reservation time in HH:MM format.'),
    }),
    outputSchema: z.object({
      available_seats: z.number(),
      booked_seats: z.number(),
      max_seats: z.number(),
      is_full: z.boolean(),
    }),
  },
  async ({ date, time }) => {
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
  }
);

// Export the tool as a callable function (optional, for direct access)
export const apiQueryAvailability = functions.https.onCall(async (request) => {
  return await queryAvailability(request.data);
});
