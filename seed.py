import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine
from app.models.complaint import Complaint, ComplaintCategory, ComplaintPriority, ComplaintStatus
from app.core.logging import logger

SEED_NAMESPACE = uuid.UUID("6ba7b810-9ded-11d1-80b4-00c04fd430c8")

SEED_COMPLAINTS = [
    # Sanitation (Urdu-influenced English: kachra, nala, smell, ganda)
    ("Bhai sahib, massive kachra heap near Commercial Market Saddar. Cleanliness team missing since 4 days, terrible smell!", "Commercial Market Saddar, Rawalpindi", ComplaintCategory.SANITATION, ComplaintPriority.HIGH),
    ("Open garbage container overflowing near Block C Gulberg. All ganda water spilling onto main street.", "Block C, Gulberg III, Lahore", ComplaintCategory.SANITATION, ComplaintPriority.MEDIUM),
    ("Nala near Sector G-7/2 blocked with plastic bags. Water accumulating during rains, big hazard.", "Sector G-7/2, Islamabad", ComplaintCategory.SANITATION, ComplaintPriority.HIGH),
    ("Sweeper has not visited Street 14 North Nazimabad for past one week. Dust and trash everywhere.", "Street 14, Block N, North Nazimabad, Karachi", ComplaintCategory.SANITATION, ComplaintPriority.LOW),
    ("Kachra Kundi outside Govt High School broken. Stray dogs scattering waste on school gate.", "Near Govt High School, Satellite Town, Gujranwala", ComplaintCategory.SANITATION, ComplaintPriority.MEDIUM),

    # Water (Urdu-influenced English: paani, tanker, pipeline leak, boring)
    ("No drinking paani in Sector F-11 since yesterday morning. WASA line broken near main roundabout.", "Sector F-11/3, Islamabad", ComplaintCategory.WATER, ComplaintPriority.CRITICAL),
    ("Meetha paani pipeline leaking heavily near Scheme 33. Thousands of gallons getting wasted!", "Main University Road, Scheme 33, Karachi", ComplaintCategory.WATER, ComplaintPriority.HIGH),
    ("Dirty sewage water mixing in main water supply pipe in Clifton Block 2. Tap water is completely black.", "Block 2, Clifton, Karachi", ComplaintCategory.WATER, ComplaintPriority.CRITICAL),
    ("Water tanker mafia blocking public hydrants in Johar Town. Residents getting no line water.", "Phase 2, Johar Town, Lahore", ComplaintCategory.WATER, ComplaintPriority.HIGH),
    ("Submersible boring pump line leaking near Park View. Muddy water covering main street.", "Park View Society, Multan", ComplaintCategory.WATER, ComplaintPriority.LOW),

    # Electricity (Urdu-influenced English: bijli, transformer, short circuit, taar, loadshedding)
    ("Transformer blast near Gali No. 5 Shahdara! Entire street without bijli in high heat.", "Gali 5, Shahdara Town, Lahore", ComplaintCategory.ELECTRICITY, ComplaintPriority.CRITICAL),
    ("Heavy spark in main electric taar outside Girls College. Risk of fire and short circuit!", "College Road, Faislabad", ComplaintCategory.ELECTRICITY, ComplaintPriority.CRITICAL),
    ("Low voltage issue in Model Town Sector B. Refrigerator and AC not functioning since 2 days.", "Sector B, Model Town, Lahore", ComplaintCategory.ELECTRICITY, ComplaintPriority.MEDIUM),
    ("Electricity pole leaning dangerously over main road after storm. Might fall any time.", "KRL Road, Rawalpindi", ComplaintCategory.ELECTRICITY, ComplaintPriority.HIGH),
    ("Unscheduled 10 hours loadshedding in Small Industrial Estate. Workers unable to operate machinery.", "Small Industrial Estate, Sialkot", ComplaintCategory.ELECTRICITY, ComplaintPriority.HIGH),

    # Roads (Urdu-influenced English: khadda, carpet road, broken, accident hazard)
    ("Huge deep khadda on Murree Road near Chandni Chowk. 3 motorbikes slipped today alone.", "Chandni Chowk, Murree Road, Rawalpindi", ComplaintCategory.ROADS, ComplaintPriority.CRITICAL),
    ("Carpet road broken due to heavy truck traffic. Manhole cover missing in middle of road.", "University Road, Peshawar", ComplaintCategory.ROADS, ComplaintPriority.HIGH),
    ("Traffic signal at Kalma Chowk underpass out of order. Massive jam every evening.", "Kalma Chowk Flyover, Lahore", ComplaintCategory.ROADS, ComplaintPriority.MEDIUM),
    ("Speed breaker near Hospital Gate constructed without warning paint or sign board.", "District Hospital Road, Sargodha", ComplaintCategory.ROADS, ComplaintPriority.LOW),
    ("Footpath encroached by illegal stalls near Saddar Metro Station. Pedestrians forced to walk on road.", "Saddar Metro Station, Hyderabad", ComplaintCategory.ROADS, ComplaintPriority.MEDIUM),

    # Public Safety (Urdu-influenced English: street light, chor, stray dogs, danger)
    ("Dark street lights not working on University Road for 2 km. Snatching incidents increasing daily.", "University Road, Quetta", ComplaintCategory.PUBLIC_SAFETY, ComplaintPriority.HIGH),
    ("Pack of aggressive stray dogs attacking children near Children Park Sector I-9.", "Sector I-9/4, Islamabad", ComplaintCategory.PUBLIC_SAFETY, ComplaintPriority.HIGH),
    ("Uncovered deep drainage hole near primary school gate. Small kids can fall inside!", "Main Gate, Govt Primary School, Sukkur", ComplaintCategory.PUBLIC_SAFETY, ComplaintPriority.CRITICAL),
    ("Dangling high voltage wires touching tree branches near residential park.", "Block 5, PECHS, Karachi", ComplaintCategory.PUBLIC_SAFETY, ComplaintPriority.CRITICAL),
    ("Illegal race driving and silencer noise late night on Ring Road. Residents unable to sleep.", "Northern Bypass Ring Road, Peshawar", ComplaintCategory.PUBLIC_SAFETY, ComplaintPriority.MEDIUM),

    # Other (Urdu-influenced English: shor, encroachment, park maintenance)
    ("Illegal commercial marriage hall operating loud DJ music till 3 AM in residential zone.", "Civil Lines, Bahawalpur", ComplaintCategory.OTHER, ComplaintPriority.MEDIUM),
    ("Public park grass uncut and benches broken. Family environment ruined by miscreants.", "Jinnah Park, Abbottabad", ComplaintCategory.OTHER, ComplaintPriority.LOW),
    ("Encroachment by auto repair workshops on residential street 8, blocking garage entrances.", "Street 8, Sector G-9/1, Islamabad", ComplaintCategory.OTHER, ComplaintPriority.MEDIUM),
    ("Dust pollution from open construction site without water sprinkling or barrier safety nets.", "DHA Phase 6, Lahore", ComplaintCategory.OTHER, ComplaintPriority.LOW),
    ("Public toilet facility at General Bus Stand in filthy unhygienic condition, locked from inside.", "General Bus Stand, Larkana", ComplaintCategory.OTHER, ComplaintPriority.LOW),
]


async def seed_data():
    """Seeds database idempotently with 30 realistic Urdu-influenced complaints."""
    async with AsyncSessionLocal() as session:
        added_count = 0
        skipped_count = 0

        for idx, (text, loc, cat, prio) in enumerate(SEED_COMPLAINTS, start=1):
            seed_id = uuid.uuid5(SEED_NAMESPACE, f"civicpulse-seed-{idx}")
            
            # Check if record already exists by ID
            stmt = select(Complaint).where(Complaint.id == seed_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                skipped_count += 1
                continue

            # Deterministic timestamps spread over past 7 days
            created_dt = datetime.now(timezone.utc) - timedelta(days=(idx % 7), hours=(idx % 24))

            complaint = Complaint(
                id=seed_id,
                text=text,
                location=loc,
                reporter_contact=f"0300-12345{idx:02d}",
                category=cat,
                priority=prio,
                status=ComplaintStatus.OPEN if idx % 3 != 0 else ComplaintStatus.IN_PROGRESS,
                ai_summary=f"Automated seed triage summary for complaint #{idx} ({cat.value}).",
                triaged_by="seed:idempotent_script",
                triage_latency_ms=12.5,
                created_at=created_dt,
                updated_at=created_dt
            )
            session.add(complaint)
            added_count += 1

        await session.commit()
        logger.info(f"Seed complete: {added_count} complaints inserted, {skipped_count} skipped (already exists).")


if __name__ == "__main__":
    asyncio.run(seed_data())
