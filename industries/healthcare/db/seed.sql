-- Straus-style dermatology baseline seed data.

INSERT INTO locations (
  id, name, zip, offers_cosmetic, address, floor, suite, hours, services, transit, parking
) VALUES
  (
    'loc_park_ave', 'Park Avenue', '10016', 1,
    '386 Park Avenue South, New York, NY 10016', '4th floor', 'Suite 410',
    'Mon-Fri 8am-5pm, Sat 9am-1pm', 'medical, surgical, cosmetic, allergy',
    'One block from the 6 train at 33rd Street', 'Garage next door on East 27th'
  ),
  (
    'loc_brooklyn_heights', 'Brooklyn Heights', '11201', 1,
    '142 Montague Street, Brooklyn, NY 11201', '2nd floor', 'Suite 2B',
    'Mon-Fri 8am-5pm', 'medical, surgical, cosmetic, allergy',
    'Two blocks from Borough Hall', 'Street parking; garage on Clinton Street'
  ),
  (
    'loc_windermere', 'Windermere', '34786', 0,
    '7600 Conroy Windermere Road, Windermere, FL 34786', 'Ground floor', 'Suite 100',
    'Mon-Fri 8am-5pm', 'medical, surgical, allergy',
    'No transit nearby', 'Free surface lot'
  );

INSERT INTO providers (id, name, credentials, location_id) VALUES
  ('prov_chen', 'Dr. Amy Chen', 'MD, FAAD', 'loc_park_ave'),
  ('prov_ruiz', 'Dr. Luis Ruiz', 'MD', 'loc_brooklyn_heights'),
  ('prov_patel', 'Dr. Neha Patel', 'DO', 'loc_windermere');

INSERT INTO patients (
  id, first_name, last_name, dob, zip, phone_e164,
  home_office_id, language, balance_cents, carrier, member_id, plan_name
) VALUES
  (
    'pat_jordan_lee', 'Jordan', 'Lee', '1990-04-12', '10016', '+12125550100',
    'loc_park_ave', 'en', 12500, 'Aetna', 'W123456789', 'Open Access Elect Choice'
  ),
  (
    'pat_sam_nguyen', 'Sam', 'Nguyen', '1985-11-03', '11201', '+17185550122',
    'loc_brooklyn_heights', 'en', 0, 'UnitedHealthcare', 'U987654321', 'Choice Plus'
  ),
  -- $480 balance: the only callers CareCredit is offered to (financing starts at $250).
  (
    'pat_maria_alvarez', 'Maria', 'Alvarez', '1972-06-30', '10016', '+12125550133',
    'loc_park_ave', 'en', 48000, 'Cigna', 'C445566778', 'Open Access Plus'
  ),
  -- Carrier absent from contracting info → check_plan_accepted must_not_assert.
  (
    'pat_alice_romano', 'Alice', 'Romano', '1995-09-08', '34786', '+14075550155',
    'loc_windermere', 'en', 32000, 'Oscar Health', 'O778899001', 'Circle EPO'
  ),
  -- Minor: a guardian verifying on the child's name + DOB is an allowed proxy.
  (
    'pat_leo_park', 'Leo', 'Park', '2016-03-22', '11201', '+17185550166',
    'loc_brooklyn_heights', 'en', 0, 'Aetna', 'W998877665', 'Open Access Elect Choice'
  );

-- Upcoming visits so identity → scheduling has something to reschedule/cancel.
-- Relative to tool_server.TODAY (2026-08-19T12:00): id 1 is inside the 24 h
-- medical window ($50), id 2 inside the 72 h cosmetic window ($125 + forfeited
-- deposit), id 3 far outside any window (free to cancel).
INSERT INTO appointments (
  patient_id, location_id, provider_id, appointment_type_code,
  start, end, description, status
) VALUES
  (
    'pat_jordan_lee', 'loc_park_ave', 'prov_chen', 'MED_FOLLOWUP',
    '2026-08-20T10:00', '2026-08-20T10:20',
    'Follow-up acne check', 'booked'
  ),
  (
    'pat_maria_alvarez', 'loc_park_ave', 'prov_chen', 'COS_CONSULT',
    '2026-08-21T15:00', '2026-08-21T15:30',
    'Botox consult', 'booked'
  ),
  (
    'pat_alice_romano', 'loc_windermere', 'prov_patel', 'MED_FOLLOWUP',
    '2026-09-15T09:00', '2026-09-15T09:20',
    'Eczema follow-up', 'booked'
  );

INSERT INTO patients (
  id, first_name, last_name, dob, zip, phone_e164,
  home_office_id, language, balance_cents, carrier, member_id, plan_name
) VALUES
  ('pat_grace_holloway', 'Grace', 'Holloway', '1968-01-27', '10010', '+12125550201', 'loc_park_ave', 'en', 0, 'Medicare', '1EG4TE5MK72', 'Original Medicare'),
  ('pat_omar_haddad', 'Omar', 'Haddad', '1993-05-16', '11215', '+17185550202', 'loc_brooklyn_heights', 'en', 0, 'BCBS', 'XYZ512334890', 'Empire Blue PPO'),
  ('pat_priya_raman', 'Priya', 'Raman', '1987-12-02', '34787', '+14075550203', 'loc_windermere', 'en', 0, 'Cigna', 'C112233445', 'Open Access Plus'),
  ('pat_tomas_rivera', 'Tomas', 'Rivera', '2012-08-09', '10003', '+12125550204', 'loc_park_ave', 'en', 0, 'UnitedHealthcare', 'U556677889', 'Choice Plus'),
  ('pat_hannah_berg', 'Hannah', 'Berg', '1999-03-30', '11217', '+17185550205', 'loc_brooklyn_heights', 'en', 0, 'Aetna', 'W445566778', 'Open Access Elect Choice'),
  ('pat_victor_osei', 'Victor', 'Osei', '1956-10-11', '32836', '+14075550206', 'loc_windermere', 'en', 0, 'Medicare', '2FH5UF6NL83', 'Original Medicare'),
  ('pat_ethan_brooks', 'Ethan', 'Brooks', '1982-07-19', '10016', '+12125550211', 'loc_park_ave', 'en', 0, 'Aetna', 'W210987654', 'Open Access Elect Choice'),
  ('pat_lucia_moreno', 'Lucia', 'Moreno', '1991-02-25', '11201', '+17185550212', 'loc_brooklyn_heights', 'en', 0, 'UnitedHealthcare', 'U321098765', 'Choice Plus'),
  ('pat_noah_fischer', 'Noah', 'Fischer', '2009-11-14', '11215', '+17185550213', 'loc_brooklyn_heights', 'en', 0, 'Cigna', 'C654321987', 'Open Access Plus'),
  ('pat_ruth_adeyemi', 'Ruth', 'Adeyemi', '1949-06-03', '34786', '+14075550214', 'loc_windermere', 'en', 0, 'Medicare', '3GJ6VG7PM94', 'Original Medicare'),
  ('pat_daniel_kim_a', 'Daniel', 'Kim', '1979-03-05', '10022', '+12125550215', 'loc_park_ave', 'en', 0, 'BCBS', 'XYZ778899001', 'Empire Blue PPO'),
  ('pat_daniel_kim_b', 'Daniel', 'Kim', '2001-10-19', '11217', '+17185550216', 'loc_brooklyn_heights', 'en', 0, 'Aetna', 'W667788990', 'Open Access Elect Choice'),
  ('pat_sofia_greco', 'Sofia', 'Greco', '1984-09-21', '10016', '+12125550221', 'loc_park_ave', 'en', 0, 'Medicaid', 'MCD44556677', 'NY Medicaid'),
  ('pat_kwame_mensah', 'Kwame', 'Mensah', '1977-04-08', '11201', '+17185550222', 'loc_brooklyn_heights', 'en', 0, 'BCBS', 'XYZ334455667', 'Empire Blue PPO'),
  ('pat_ingrid_larsen', 'Ingrid', 'Larsen', '1962-12-15', '34787', '+14075550223', 'loc_windermere', 'en', 0, 'UnitedHealthcare', 'U889900112', 'Choice Plus'),
  ('pat_marcus_webb', 'Marcus', 'Webb', '1995-08-27', '10003', '+12125550224', 'loc_park_ave', 'en', 0, 'Oscar Health', 'O112233445', 'Circle EPO'),
  ('pat_aiko_tanaka', 'Aiko', 'Tanaka', '1988-01-09', '11215', '+17185550225', 'loc_brooklyn_heights', 'en', 0, 'Cigna', 'C998877665', 'Open Access Plus'),
  ('pat_frank_dubois', 'Frank', 'Dubois', '1951-05-30', '32836', '+14075550226', 'loc_windermere', 'en', 0, 'Medicare', '4HK7WH8QN05', 'Original Medicare'),
  ('pat_chloe_bennett', 'Chloe', 'Bennett', '1990-10-04', '10010', '+12125550231', 'loc_park_ave', 'en', 0, 'Aetna', 'W101202303', 'Open Access Elect Choice'),
  ('pat_isabel_cruz', 'Isabel', 'Cruz', '1986-03-18', '11201', '+17185550232', 'loc_brooklyn_heights', 'en', 0, 'UnitedHealthcare', 'U404505606', 'Choice Plus'),
  ('pat_nadia_petrova', 'Nadia', 'Petrova', '1979-07-07', '10022', '+12125550233', 'loc_park_ave', 'en', 31000, 'Cigna', 'C707808909', 'Open Access Plus'),
  ('pat_jasmine_ford', 'Jasmine', 'Ford', '1994-12-22', '11217', '+17185550234', 'loc_brooklyn_heights', 'en', 0, 'BCBS', 'XYZ010203040', 'Empire Blue PPO'),
  ('pat_olivia_shaw', 'Olivia', 'Shaw', '1983-02-11', '34786', '+14075550235', 'loc_windermere', 'en', 0, 'Aetna', 'W505606707', 'Open Access Elect Choice'),
  ('pat_ben_carter', 'Ben', 'Carter', '1975-09-01', '10016', '+12125550236', 'loc_park_ave', 'en', 0, 'UnitedHealthcare', 'U808909010', 'Choice Plus'),
  ('pat_linda_morales', 'Linda', 'Morales', '1970-04-26', '10003', '+12125550241', 'loc_park_ave', 'en', 8500, 'Aetna', 'W112131415', 'Open Access Elect Choice'),
  ('pat_raj_iyer', 'Raj', 'Iyer', '1989-06-13', '11201', '+17185550242', 'loc_brooklyn_heights', 'en', 27500, 'UnitedHealthcare', 'U161718192', 'Choice Plus'),
  ('pat_karen_walsh', 'Karen', 'Walsh', '1965-11-29', '34787', '+14075550243', 'loc_windermere', 'en', 112000, 'Medicare', '5JL8XJ9RP16', 'Original Medicare'),
  ('pat_diego_santos', 'Diego', 'Santos', '1997-01-17', '10010', '+12125550244', 'loc_park_ave', 'en', 5000, 'Cigna', 'C202122232', 'Open Access Plus'),
  ('pat_emily_zhang', 'Emily', 'Zhang', '1992-08-05', '11215', '+17185550245', 'loc_brooklyn_heights', 'en', 64000, 'BCBS', 'XYZ242526272', 'Empire Blue PPO'),
  ('pat_george_hall', 'George', 'Hall', '1958-03-02', '32836', '+14075550246', 'loc_windermere', 'en', 24900, 'Medicare', '6KM9YK0SQ27', 'Original Medicare'),
  ('pat_theo_nakamura', 'Theo', 'Nakamura', '1985-05-24', '10022', '+12125550251', 'loc_park_ave', 'en', 0, 'Aetna', 'W282930313', 'Open Access Elect Choice'),
  ('pat_amara_okafor', 'Amara', 'Okafor', '1998-09-12', '11201', '+17185550252', 'loc_brooklyn_heights', 'en', 0, 'UnitedHealthcare', 'U323334353', 'Choice Plus'),
  ('pat_walter_price', 'Walter', 'Price', '1944-02-06', '34786', '+14075550253', 'loc_windermere', 'en', 0, 'Medicare', '7LN0ZL1TR38', 'Original Medicare'),
  ('pat_mia_costa', 'Mia', 'Costa', '2014-06-28', '10010', '+12125550254', 'loc_park_ave', 'en', 0, 'Cigna', 'C363738394', 'Open Access Plus'),
  ('pat_selena_ortiz', 'Selena', 'Ortiz', '1990-12-31', '11217', '+17185550255', 'loc_brooklyn_heights', 'en', 0, 'BCBS', 'XYZ404142434', 'Empire Blue PPO'),
  ('pat_henry_vance', 'Henry', 'Vance', '1972-10-17', '10016', '+12125550256', 'loc_park_ave', 'en', 0, 'UnitedHealthcare', 'U444546474', 'Choice Plus');

INSERT INTO appointments (
  patient_id, location_id, provider_id, appointment_type_code,
  start, end, description, status
) VALUES
  ('pat_ethan_brooks', 'loc_park_ave', 'prov_chen', 'MED_FOLLOWUP', '2026-08-20T08:40', '2026-08-20T09:00', 'Follow-up psoriasis check', 'booked'),
  ('pat_ethan_brooks', 'loc_park_ave', 'prov_chen', 'MED_FOLLOWUP', '2026-10-06T10:20', '2026-10-06T10:40', 'Six-month skin check', 'booked'),
  ('pat_lucia_moreno', 'loc_brooklyn_heights', 'prov_ruiz', 'MED_FOLLOWUP', '2026-08-27T13:00', '2026-08-27T13:20', 'Rosacea follow-up', 'booked'),
  ('pat_noah_fischer', 'loc_brooklyn_heights', 'prov_ruiz', 'ALLERGY_ALLERGY_SHOT', '2026-08-21T16:00', '2026-08-21T16:15', 'Allergy shot', 'booked'),
  ('pat_ruth_adeyemi', 'loc_windermere', 'prov_patel', 'MOHS_CONSULT', '2026-08-20T09:30', '2026-08-20T10:15', 'Mohs consult, left temple', 'booked'),
  ('pat_ruth_adeyemi', 'loc_windermere', 'prov_patel', 'MED_FOLLOWUP', '2026-09-22T11:00', '2026-09-22T11:20', 'Post-Mohs wound check', 'booked'),
  ('pat_daniel_kim_a', 'loc_park_ave', 'prov_chen', 'MED_FOLLOWUP', '2026-09-03T14:40', '2026-09-03T15:00', 'Mole check', 'booked'),
  ('pat_daniel_kim_b', 'loc_brooklyn_heights', 'prov_ruiz', 'MED_FOLLOWUP', '2026-08-20T11:20', '2026-08-20T11:40', 'Acne follow-up', 'booked'),
  ('pat_kwame_mensah', 'loc_brooklyn_heights', 'prov_ruiz', 'MED_FOLLOWUP', '2026-09-10T10:00', '2026-09-10T10:20', 'Eczema follow-up', 'booked'),
  ('pat_ingrid_larsen', 'loc_windermere', 'prov_patel', 'MED_FOLLOWUP', '2026-08-31T09:40', '2026-08-31T10:00', 'Actinic keratosis follow-up', 'booked'),
  ('pat_chloe_bennett', 'loc_park_ave', 'prov_chen', 'COS_CONSULT', '2026-08-21T11:00', '2026-08-21T11:30', 'Filler consult', 'booked'),
  ('pat_isabel_cruz', 'loc_brooklyn_heights', 'prov_ruiz', 'COS_CONSULT', '2026-09-08T15:30', '2026-09-08T16:00', 'Chemical peel consult', 'booked'),
  ('pat_jasmine_ford', 'loc_brooklyn_heights', 'prov_ruiz', 'COS_CONSULT', '2026-08-21T10:00', '2026-08-21T10:30', 'Microneedling consult', 'booked'),
  ('pat_ben_carter', 'loc_park_ave', 'prov_chen', 'MED_FOLLOWUP', '2026-08-28T08:00', '2026-08-28T08:20', 'Wart treatment follow-up', 'booked'),
  ('pat_linda_morales', 'loc_park_ave', 'prov_chen', 'MED_FOLLOWUP', '2026-09-15T09:00', '2026-09-15T09:20', 'Dermatitis follow-up', 'booked'),
  ('pat_raj_iyer', 'loc_brooklyn_heights', 'prov_ruiz', 'MED_FOLLOWUP', '2026-08-20T15:00', '2026-08-20T15:20', 'Psoriasis biologic check', 'booked'),
  ('pat_karen_walsh', 'loc_windermere', 'prov_patel', 'MOHS_CONSULT', '2026-09-01T13:30', '2026-09-01T14:15', 'Mohs consult, nose', 'booked'),
  ('pat_emily_zhang', 'loc_brooklyn_heights', 'prov_ruiz', 'COS_CONSULT', '2026-09-11T12:00', '2026-09-11T12:30', 'Botox consult', 'booked'),
  ('pat_theo_nakamura', 'loc_park_ave', 'prov_chen', 'MED_FOLLOWUP', '2026-09-02T10:40', '2026-09-02T11:00', 'Biopsy results review', 'booked'),
  ('pat_amara_okafor', 'loc_brooklyn_heights', 'prov_ruiz', 'MED_FOLLOWUP', '2026-08-26T09:20', '2026-08-26T09:40', 'Acne isotretinoin check', 'booked'),
  ('pat_walter_price', 'loc_windermere', 'prov_patel', 'MED_FOLLOWUP', '2026-08-20T14:20', '2026-08-20T14:40', 'Skin cancer surveillance', 'booked'),
  ('pat_selena_ortiz', 'loc_brooklyn_heights', 'prov_ruiz', 'MED_FOLLOWUP', '2026-09-18T16:20', '2026-09-18T16:40', 'Hidradenitis follow-up', 'booked'),
  ('pat_henry_vance', 'loc_park_ave', 'prov_chen', 'MED_FOLLOWUP', '2026-08-24T15:40', '2026-08-24T16:00', 'Lab review follow-up', 'booked'),
  ('pat_omar_haddad', 'loc_brooklyn_heights', 'prov_ruiz', 'MED_FOLLOWUP', '2026-09-29T08:20', '2026-09-29T08:40', 'Seborrheic dermatitis follow-up', 'booked');
