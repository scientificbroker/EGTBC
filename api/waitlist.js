import { createClient } from '@supabase/supabase-js';

export default async function handler(req, res) {
    // Enable CORS for localhost during development, Vercel handles it in prod usually
    res.setHeader('Access-Control-Allow-Credentials', true);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
    res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');

    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }

    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    const { name, email, institution, profile } = req.body;

    if (!name || !email) {
        return res.status(400).json({ error: 'Name and Email are required' });
    }

    // Initialize Supabase client
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_ANON_KEY;
    
    if (!supabaseUrl || !supabaseKey) {
        return res.status(500).json({ error: 'Supabase credentials not configured' });
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    try {
        const { data, error } = await supabase
            .from('waitlist')
            .insert([
                { name, email, institution, profile }
            ]);

        if (error) {
            if (error.code === '23505') { // Postgres unique violation error code
                return res.status(400).json({ error: 'Email already registered' });
            }
            return res.status(500).json({ error: error.message });
        }

        return res.status(201).json({ message: 'Successfully joined the waitlist' });
    } catch (err) {
        return res.status(500).json({ error: 'Internal server error' });
    }
}
