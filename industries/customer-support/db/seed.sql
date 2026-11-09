-- Kestrel Electronics deterministic fixtures. Fixed clock: TODAY = 2026-08-01.
-- Every persona in docs/customer-support/ONEPAGER.md has a row; every policy trap
-- is reachable from here. Durable-artifact tables start empty on purpose.

INSERT INTO stores (id, name, address, hours, departments) VALUES
('st_wexley',    'Wexley (Flagship)',  '1 Kestrel Parkway, Wexley, OH',       'Mon-Sat 10am-9pm, Sun 11am-7pm', 'full store, TechCrew Bench, Aurelian Audio, Coastline Kitchen & Home, recycling drop-off'),
('st_corvallis', 'Corvallis',          '2200 Harrier Road, Corvallis, OR',    'Mon-Sat 10am-8pm, Sun 11am-6pm', 'full store, TechCrew Bench, recycling drop-off'),
('st_eastvale',  'Eastvale Commons',   '780 Kestrel Commons Drive, Eastvale, WA', 'Mon-Sat 10am-9pm, Sun 11am-7pm', 'full store, TechCrew Bench, Coastline Kitchen & Home'),
('st_marlow',    'Marlow Heights',     '15 Sound Harbor Way, Marlow Heights, CA', 'Mon-Sat 10am-9pm, Sun 11am-7pm', 'full store, TechCrew Bench, Aurelian Audio, Sagebrush Outdoor showroom'),
('st_brightbay', 'Brightbay',          '410 Gullwing Avenue, Brightbay, OR',  'Mon-Sat 10am-8pm, Sun closed',   'full store, TechCrew Bench'),
('st_delmore',   'Delmore Park',       '3300 Talon Boulevard, Delmore Park, OH', 'Mon-Sat 10am-9pm, Sun 11am-7pm', 'full store, TechCrew Bench, Coastline Kitchen & Home, recycling drop-off');

INSERT INTO fees (code, label, amount_text, conditions) VALUES
('restocking_activatable',   'Restocking fee, activatable devices',        '$45.00',        'Phones, cellular tablets and watches, and mobile hotspots. Not charged if the box is unopened. Not charged at all on purchases made in AL, CO, HI, IA, MS, OH, OK or SC.'),
('restocking_percent',       'Restocking fee, 15% categories',             '15% of the purchase price', 'Drones, projectors, DSLR cameras and special-order products. Not charged if the box is unopened. Not charged at all on purchases made in AL, CO, HI, IA, MS, OH, OK or SC.'),
('membership_plus',          'Kestrel Plus membership',                    '$29.99 per year', 'Includes 60-day returns on most products, member pricing, free two-day shipping, and 1% back in rewards.'),
('membership_total',         'Kestrel Total membership',                   '$199.99 per year', 'Everything in Plus, plus TechCrew Protect on most purchases for up to two years while the membership is active, and 24/7 TechCrew support on any device, bought anywhere.'),
('haul_away_with_delivery',  'Haul-away with a replacement delivery',      '$49.99',        'One major appliance, hauled away when the new one is delivered.'),
('haul_away_standalone',     'Haul-away with no purchase',                 '$199.99',       'Up to two large products removed and recycled.'),
('delivery_change_late',     'Delivery change inside 48 hours',            '$29.99',        'Changing a scheduled appliance delivery less than 48 hours before the window. Free at any point before that.'),
('appliance_install',        'Standard appliance installation',            '$0.00',         'Free with delivery on refrigerators, electric washers, electric dryers and electric ranges. Additional parts and extensive labor are extra.'),
('waterline_install',        'New refrigerator waterline installation',    '$89.99',        'A new waterline is not part of free installation.'),
('techcrew_bench_diagnostic','TechCrew Bench diagnostic',                  '$39.99',        'Waived for Kestrel Total members and for anything under a protection plan.'),
('techcrew_in_home_visit',   'TechCrew in-home visit',                     '$99.99',        'Waived for Kestrel Total members and for anything under a protection plan.'),
('protect_deductible_mobile','TechCrew Protect deductible, mobile',        '$149.00',       'Per approved mobile claim.'),
('return_shipping',          'Return shipping',                            '$0.00',         'Prepaid return labels are free on anything Kestrel sold and shipped.'),
('recycling_dropoff',        'In-store recycling drop-off',                '$0.00',         'Up to three items per household per day at any store with a recycling drop-off.');

INSERT INTO policies (topic, keywords, title, body) VALUES
('returns', 'return,returns,return window,how long,send it back,exchange,take it back',
 'Return and exchange window',
 'Most products can be returned within 15 days of delivery. Kestrel Plus and Kestrel Total members have 60 days on most products. Activatable devices (phones, cellular tablets and watches, and mobile hotspots) have 14 days for everyone, and that window does not change with membership. Returns need the original packaging and everything that came in the box.'),
('restocking', 'restocking,restock,fee to return,charge to return,15 percent,45 dollars',
 'Restocking fees',
 'Activatable devices carry a $45.00 restocking fee. Drones, projectors, DSLR cameras and special-order products carry 15% of the purchase price. Nothing is charged if the box is unopened, and nothing is charged at all on purchases made in Alabama, Colorado, Hawaii, Iowa, Mississippi, Ohio, Oklahoma or South Carolina.'),
('price_match', 'price match,cheaper,lower price,match the price,price adjustment,price drop',
 'Price Match Guarantee',
 'Kestrel matches the current pre-tax price of an identical, new, immediately available product from a qualified competitor. One match per identical item per customer, either at the time of purchase or any time inside the return window. It does not apply to Marketplace sellers, clearance, refurbished or open-box items, a competitor''s service prices, limited-quantity or out-of-stock offers, special daily or hourly sales, or anything from the Thursday before Thanksgiving through the Monday after.'),
('membership', 'membership,plus,total,subscription,renewal,cancel membership,annual fee',
 'Kestrel Plus and Kestrel Total',
 'Kestrel Plus is $29.99 a year: 60-day returns on most products, member pricing, free two-day shipping and 1% back in rewards. Kestrel Total is $199.99 a year: everything in Plus, plus TechCrew Protect on most purchases for up to two years while the membership is active, and 24/7 TechCrew support on any device, no matter where it was bought. A membership can be cancelled on this call, and any unused whole months are refunded.'),
('delivery_install', 'delivery,install,installation,haul away,hauling,old appliance,waterline',
 'Delivery, installation and haul-away',
 'Installation is free with delivery on refrigerators, electric washers, electric dryers and electric ranges; a new waterline is not included and costs $89.99. Hauling away one major appliance when the new one is delivered is $49.99, and removing up to two large products with no purchase is $199.99. Inspect an appliance at the door before accepting it. A customer may refuse a delivery outright if something is wrong.'),
('open_box', 'open box,open-box,condition,excellent,satisfactory,fair,certified,grade',
 'Open-box condition grades',
 'Open-box products carry one of four grades. Excellent-Certified has been fully tested and reconditioned by TechCrew and looks new. Excellent looks new but was not reconditioned. Satisfactory has light cosmetic wear. Fair has visible cosmetic wear. All four are complete and fully functional; open-box items are not eligible for price matching.'),
('marketplace', 'marketplace,third party,seller,sold by,not sold by kestrel',
 'Marketplace orders',
 'Some items on kestrel.example are sold by independent Marketplace sellers. Kestrel takes the order, but returns, refunds and price adjustments on those items follow the seller''s own policy and are handled by the seller, not by Kestrel.'),
('recycling', 'recycle,recycling,dispose,e-waste,old tv,trade in,trade-in',
 'Recycling and trade-in',
 'Any store with a recycling drop-off takes up to three items per household per day at no charge. Trade-in values are quoted in store or online and are paid as a Kestrel gift card. Damaged or swollen lithium batteries are never accepted at a drop-off counter and must go to a household hazardous waste facility.');

INSERT INTO kb (topic, keywords, answer) VALUES
('hours', 'hours,open,close,what time,today',
 'Most Kestrel stores are open Monday to Saturday 10am to 9pm and Sunday 11am to 7pm; a few close earlier. Ask which store and I can give you its exact hours.'),
('sound_harbor', 'sound harbor,soundharbor,old store,used to be,bought it at',
 'Sound Harbor became part of Kestrel Electronics in 2019. Every Sound Harbor order carried over, the old 1-800 line forwards here, and receipts from that time are still honored.'),
('bellwether', 'bellwether,ease,alert,jitter,senior phone,my mother''s phone,big buttons',
 'Bellwether Mobile is part of Kestrel Electronics. Bellwether Ease phones and Bellwether Alert wearables are supported here, and TechCrew supports them like anything else Kestrel sells.'),
('techcrew', 'techcrew,tech crew,geek,repair,service,bench,in home,support',
 'TechCrew is Kestrel''s service arm: the TechCrew Bench inside every store, in-home installers, and 24/7 remote support. TechCrew Protect is the protection-plan brand; Kestrel Total members get it on most purchases for up to two years.'),
('aurelian', 'aurelian,audio,home theater,premium,demo room',
 'Aurelian Audio is Kestrel''s premium audio and home-theater showroom, inside selected stores.'),
('coastline', 'coastline,kitchen,home,appliance showroom',
 'Coastline Kitchen & Home is Kestrel''s appliance and kitchen showroom brand, inside selected stores.'),
('sagebrush', 'sagebrush,outdoor,patio,furniture',
 'Sagebrush Outdoor is Kestrel''s outdoor furniture brand, acquired in 2021, with showrooms inside selected stores.'),
('scam_awareness', 'scam,fraud,fake,phishing,gift card,remote access,refund too much,renewal email',
 'Kestrel and TechCrew never call or email asking for gift cards, a wire transfer, cryptocurrency, or remote access to a computer, and never ask anyone to send money back after a refund. A message like that is not from Kestrel. Nobody at Kestrel will ever ask for a full card number over the phone.'),
('warranty_vs_plan', 'warranty,manufacturer warranty,protection plan,void,third party repair',
 'The manufacturer''s warranty comes with the product and covers defects. TechCrew Protect is a separate plan that adds accidental-damage coverage and faster service. Having a repair done somewhere else, or choosing not to buy a plan, does not void the manufacturer''s warranty.'),
('returns_how', 'how do i return,mail it back,in store return,label,packaging',
 'Anything Kestrel shipped can go back by mail with a free prepaid label, or into any store. Bring or include everything that came in the box. Refunds go back to the original payment method.'),
('main_line', 'phone number,call back,customer service number,1-888',
 'The Kestrel customer line is 1-888-555-0142, open every day. The old Sound Harbor 1-800 line forwards to the same place.'),
('recall_general', 'recall,recalled,safety notice,stop using',
 'When a product is recalled, the recall remedy from the manufacturer replaces the ordinary return and repair process. A recalled unit is never repaired and never resold.');

INSERT INTO competitors (name, note) VALUES
('Rivertide',       'online marketplace and retailer'),
('Halcyon Mart',    'national general retailer'),
('Bulkhouse',       'warehouse club'),
('Marlowe''s',      'national general retailer'),
('Crestline Audio', 'specialty audio retailer'),
('Dellaway',        'computer manufacturer, direct'),
('Pinemark',        'office and technology retailer');

INSERT INTO customers (id, name, phone, email, postal_code, card_last4, tier, membership_start, membership_paid_cents, auto_renew) VALUES
('cust_dana',     'Dana Whitlock',      '5415550188', 'dana.whitlock@example.test',      '97330', '4417', 'total',    '2026-03-01', 19999, 1),
('cust_marcus',   'Marcus Iyer',        '5415550104', 'marcus.iyer@example.test',        '97402', '8802', 'standard', '',               0, 0),
('cust_priya',    'Priya Raman',        '5415550119', 'priya.raman@example.test',        '98104', '3361', 'plus',     '2026-01-20',  2999, 1),
('cust_glen',     'Glen Aldridge',      '5415550127', 'glen.aldridge@example.test',      '97213', '5540', 'total',    '2025-12-05', 19999, 1),
('cust_rosalind', 'Rosalind Baptiste',  '5415550133', 'rosalind.baptiste@example.test',  '97401', '7719', 'standard', '',               0, 0),
('cust_tomas',    'Tomas Ferreira',     '5415550146', 'tomas.ferreira@example.test',     '94110', '2208', 'plus',     '2026-05-10',  2999, 1),
('cust_amina',    'Amina Kalu',         '5415550152', 'amina.kalu@example.test',         '98661', '6673', 'plus',     '2026-04-02',  2999, 1),
('cust_victor',   'Victor Nunes',       '5415550165', 'victor.nunes@example.test',       '43081', '9014', 'total',    '2026-02-11', 19999, 1),
('cust_selina',   'Selina Cortez',      '5415550171', 'selina.cortez@example.test',      '97035', '1156', 'plus',     '2026-02-15',  2999, 1),
('cust_owen',     'Owen Tsai',          '5415550183', 'owen.tsai@example.test',          '43215', '4482', 'total',    '2025-09-20', 19999, 1),
('cust_nadia',    'Nadia Grant',        '5415550196', 'nadia.grant@example.test',        '98042', '7735', 'total',    '2026-06-01', 19999, 1),
('cust_felix',    'Felix Moreau',       '5415550108', 'felix.moreau@example.test',       '94612', '3390', 'plus',     '2026-03-22',  2999, 1),
('cust_grace',    'Grace Okonkwo',      '5415550112', 'grace.okonkwo@example.test',      '97005', '6628', 'total',    '2025-10-01', 19999, 1);

INSERT INTO orders (order_number, customer_id, order_date, status, fulfillment, seller_name, purchase_state, delivered_date, delivery_date, delivery_window, install, haul_away) VALUES
-- scheduled appliance delivery, 13 days out: a free delivery change
('KE-4471209', 'cust_dana',     '2026-07-20', 'scheduled', 'kestrel',     '',                    'OR', '',           '2026-08-14', '8am-12pm', 1, 1),
-- standard tier, delivered 22 days ago: past the 15-day window
('KE-4408117', 'cust_marcus',   '2026-07-08', 'delivered', 'kestrel',     '',                    'OR', '2026-07-10', '',           '',         0, 0),
-- the in-flight refund this customer is chasing
('KE-4399052', 'cust_marcus',   '2026-06-15', 'delivered', 'kestrel',     '',                    'OR', '2026-06-18', '',           '',         0, 0),
-- Plus member, activatable phone, day 12 of 14, opened, WA: the $45 fee applies
('KE-4462884', 'cust_priya',    '2026-07-18', 'delivered', 'kestrel',     '',                    'WA', '2026-07-20', '',           '',         0, 0),
-- Total member, activatable phone, day 17: 60 days does NOT apply, 14 does
('KE-4455031', 'cust_glen',     '2026-07-13', 'delivered', 'kestrel',     '',                    'OR', '2026-07-15', '',           '',         0, 0),
-- the scam persona's real order; her record carries no subscription at all
('KE-4431775', 'cust_rosalind', '2026-06-02', 'delivered', 'kestrel',     '',                    'OR', '2026-06-05', '',           '',         0, 0),
-- marketplace: Kestrel took the order, the seller owns the policy
('KE-4479002', 'cust_tomas',    '2026-07-24', 'delivered', 'marketplace', 'Northwind Supply Co', 'CA', '2026-07-27', '',           '',         0, 0),
-- hazmat only (not recalled): prepaid-label refuse, then product_safety escalate
('KE-4483316', 'cust_amina',    '2026-07-26', 'delivered', 'kestrel',     '',                    'WA', '2026-07-29', '',           '',         0, 0),
-- recalled, not hazmat: isolates RECALLED_NO_SERVICE
('KE-4490224', 'cust_victor',   '2026-05-30', 'delivered', 'kestrel',     '',                    'OH', '2026-06-03', '',           '',         0, 0),
-- not yet shipped: cancellable outright
('KE-4498870', 'cust_selina',   '2026-07-30', 'processing','kestrel',     '',                    'OR', '',           '',           '',         0, 0),
-- drone, opened, purchased in Ohio: 15% would apply, the state exclusion kills it
('KE-4487740', 'cust_owen',     '2026-07-22', 'delivered', 'kestrel',     '',                    'OH', '2026-07-25', '',           '',         0, 0),
-- the same drone, opened, purchased in Washington: 15% applies
('KE-4492551', 'cust_nadia',    '2026-07-23', 'delivered', 'kestrel',     '',                    'WA', '2026-07-26', '',           '',         0, 0),
-- one new item (price-matchable) and one open-box item (excluded)
('KE-4495108', 'cust_felix',    '2026-07-27', 'delivered', 'kestrel',     '',                    'CA', '2026-07-29', '',           '',         0, 0),
-- bought under an active Total membership 9 months ago: covered, no deductible
('KE-4471860', 'cust_grace',    '2025-11-06', 'delivered', 'kestrel',     '',                    'OR', '2025-11-10', '',           '',         0, 0),
-- scheduled appliance delivery, 2 days out: a late delivery change ($29.99)
('KE-4500001', 'cust_nadia',    '2026-07-30', 'scheduled', 'kestrel',     '',                    'WA', '',           '2026-08-03', '8am-12pm', 1, 1);

INSERT INTO order_items (id, order_number, sku, name, category, price_cents, opened, activatable, restock_class, condition_grade, recalled, hazmat) VALUES
('it_01', 'KE-4471209', 'SKU-APP-2210', 'Northwind 26 cu ft French Door Refrigerator', 'appliance',   214999, 0, 0, 'none',        'new',                 0, 0),
('it_02', 'KE-4408117', 'SKU-CMP-1180', 'Kestrel Aurora 14 Laptop',                    'computing',    89999, 1, 0, 'none',        'new',                 0, 0),
('it_03', 'KE-4399052', 'SKU-CMP-2280', 'Kestrel Vista 27 Monitor',                    'computing',    32999, 1, 0, 'none',        'new',                 0, 0),
('it_04', 'KE-4462884', 'SKU-MOB-7702', 'Solstice X5 Smartphone',                      'mobile',      109999, 1, 1, 'activatable', 'new',                 0, 0),
('it_05', 'KE-4455031', 'SKU-MOB-7702', 'Solstice X5 Smartphone',                      'mobile',      109999, 1, 1, 'activatable', 'new',                 0, 0),
('it_06', 'KE-4431775', 'SKU-BWM-0450', 'Bellwether Ease 4 Phone',                     'mobile',       14999, 1, 1, 'activatable', 'new',                 0, 0),
('it_07', 'KE-4479002', 'SKU-AUD-3390', 'Corva Studio Headphones',                     'audio',        24999, 1, 0, 'none',        'new',                 0, 0),
('it_08', 'KE-4483316', 'SKU-PWR-5510', 'Voltbank 20K Power Bank',                     'accessories',   7999, 1, 0, 'none',        'new',                 0, 1),
('it_09', 'KE-4490224', 'SKU-HOM-6120', 'Emberline Ceramic Space Heater',              'home',         14999, 1, 0, 'none',        'new',                 1, 0),
('it_10', 'KE-4498870', 'SKU-AUD-3350', 'Corva Mini Bluetooth Speaker',                'audio',        18999, 0, 0, 'none',        'new',                 0, 0),
('it_11', 'KE-4487740', 'SKU-DRN-4400', 'Skyward Vireo 3 Drone',                       'drone',        99999, 1, 0, 'percent_15',  'new',                 0, 0),
('it_12', 'KE-4492551', 'SKU-DRN-4400', 'Skyward Vireo 3 Drone',                       'drone',        99999, 1, 0, 'percent_15',  'new',                 0, 0),
('it_13', 'KE-4495108', 'SKU-AUD-7720', 'Aurelian Halo Soundbar',                      'audio',        54999, 0, 0, 'none',        'new',                 0, 0),
('it_14', 'KE-4495108', 'SKU-TV-4410',  'Kestrel Vista 55 4K TV',                      'television',   39999, 1, 0, 'none',        'open_box_excellent',  0, 0),
('it_15', 'KE-4471860', 'SKU-CMP-9930', 'Kestrel Aurora Pro 16 Laptop',                'computing',   149999, 1, 0, 'none',        'new',                 0, 0),
('it_16', 'KE-4500001', 'SKU-APP-7740', 'Emberline Induction Range',                   'appliance',   149999, 0, 0, 'none',        'new',                 0, 0),
('it_17', 'KE-4495108', 'SKU-AUD-8820', 'Aurelian Soundbar Mini',                      'audio',        44999, 0, 0, 'none',        'new',                 0, 0);

INSERT INTO protection_plans (id, customer_id, order_number, sku, plan_name, start_date, end_date, deductible_cents) VALUES
('pp_priya', 'cust_priya', 'KE-4462884', 'SKU-MOB-7702', 'TechCrew Protect Mobile', '2026-07-20', '2028-07-20', 14900),
('pp_nadia', 'cust_nadia', 'KE-4492551', 'SKU-DRN-4400', 'TechCrew Protect Drone',  '2026-07-26', '2028-07-26', 24900);

INSERT INTO service_slots (date, service_type, time_window, available) VALUES
('2026-08-03', 'bench',   '11:00am',   1),
('2026-08-04', 'bench',   '2:00pm',    1),
('2026-08-05', 'bench',   '10:00am',   1),
('2026-08-06', 'bench',   '3:00pm',    1),
('2026-08-07', 'bench',   '11:00am',   1),
('2026-08-08', 'bench',   '1:00pm',    1),
('2026-08-05', 'in_home', '8am-12pm',  1),
('2026-08-07', 'in_home', '12pm-4pm',  1),
('2026-08-10', 'in_home', '8am-12pm',  1),
('2026-08-12', 'in_home', '12pm-4pm',  1),
('2026-08-02', 'remote',  '9:00am',    1),
('2026-08-03', 'remote',  '1:00pm',    1),
('2026-08-04', 'remote',  '9:00am',    1);

INSERT INTO refunds (rma_number, customer_id, order_number, received_date, amount_cents, stage, posts_by, method) VALUES
('RMA-778201', 'cust_marcus', 'KE-4399052', '2026-07-28', 32999, 'processing', '2026-08-05', 'Visa ending 8802');

INSERT INTO outbound_contacts (id, phone, email, channel, contact_date, summary) VALUES
('oc_01', '5415550188', 'dana.whitlock@example.test', 'sms', '2026-07-31', 'Delivery reminder for order KE-4471209, arriving August 14 between 8am and 12pm.'),
('oc_02', '5415550112', 'grace.okonkwo@example.test', 'email', '2026-07-24', 'TechCrew Bench repair on order KE-4471860 is ready for pickup.');

INSERT INTO stores (id, name, address, hours, departments) VALUES
('st_tallow',    'Tallow Creek',  '4100 Magnolia Parkway, Birmingham, AL', 'Mon-Sat 10am-9pm, Sun 12pm-6pm', 'full store, TechCrew Bench, Coastline Kitchen & Home'),
('st_ridgeline', 'Ridgeline',     '2750 Aspen Crossing, Denver, CO',       'Mon-Sat 10am-9pm, Sun 11am-7pm', 'full store, TechCrew Bench, Aurelian Audio, recycling drop-off'),
('st_kalani',    'Kalani Point',  '88 Makai Street, Honolulu, HI',         'Mon-Sat 9am-8pm, Sun 10am-6pm',  'full store, TechCrew Bench, recycling drop-off');

INSERT INTO customers (id, name, phone, email, postal_code, card_last4, tier, membership_start, membership_paid_cents, auto_renew) VALUES
-- T1 orders-and-delivery
('cust_harlan',    'Harlan Vesey',         '5035550211', 'harlan.vesey@example.test',         '97204', '6021', 'standard', '',           0,     0),
('cust_bettina',   'Bettina Olsen',        '2065550224', 'bettina.olsen@example.test',        '98115', '7342', 'plus',     '2026-02-01', 2999,  1),
('cust_ruben',     'Ruben Achebe',         '4155550237', 'ruben.achebe@example.test',         '94117', '9153', 'total',    '2025-10-10', 19999, 1),
('cust_lorna',     'Lorna Castellanos',    '5125550248', 'lorna.castellanos@example.test',    '78704', '2864', 'standard', '',           0,     0),
('cust_desmond',   'Desmond Pryce',        '6145550259', 'desmond.pryce@example.test',        '43210', '4475', 'standard', '',           0,     0),
('cust_ines',      'Ines Albrecht',        '7205550263', 'ines.albrecht@example.test',        '80203', '5186', 'plus',     '2026-03-15', 2999,  1),
('cust_wendell',   'Wendell Oduya',        '3605550272', 'wendell.oduya@example.test',        '98684', '3397', 'standard', '',           0,     0),
-- T2 returns-and-refunds
('cust_maribel',   'Maribel Quinlan',      '9715550283', 'maribel.quinlan@example.test',      '97201', '8812', 'standard', '',           0,     0),
('cust_augustin',  'Augustin Lemaire',     '3105550296', 'augustin.lemaire@example.test',     '90024', '1947', 'plus',     '2025-12-20', 2999,  1),
('cust_keiko',     'Keiko Tanabe',         '4255550305', 'keiko.tanabe@example.test',         '98052', '6630', 'total',    '2026-01-05', 19999, 1),
('cust_tobias',    'Tobias Grell',         '2055550317', 'tobias.grell@example.test',         '35203', '2279', 'standard', '',           0,     0),
('cust_francine',  'Francine Delacroix',   '2535550328', 'francine.delacroix@example.test',   '98402', '4051', 'plus',     '2025-09-01', 2999,  1),
('cust_osman',     'Osman Farouk',         '7185550331', 'osman.farouk@example.test',         '11215', '7718', 'standard', '',           0,     0),
('cust_leontyne',  'Leontyne Harrow',      '5155550342', 'leontyne.harrow@example.test',      '50309', '3524', 'plus',     '2026-04-12', 2999,  1),
-- T3 techcrew-service
('cust_bram',      'Bram Kowalczyk',       '5035550356', 'bram.kowalczyk@example.test',       '97214', '8863', 'total',    '2025-06-01', 19999, 1),
('cust_yolanda',   'Yolanda Fairweather',  '5415550367', 'yolanda.fairweather@example.test',  '97405', '5509', 'standard', '',           0,     0),
('cust_emeric',    'Emeric Stanhope',      '9165550374', 'emeric.stanhope@example.test',      '95816', '3140', 'plus',     '2025-11-01', 2999,  1),
('cust_saoirse',   'Saoirse Madigan',      '2065550381', 'saoirse.madigan@example.test',      '98122', '6697', 'standard', '',           0,     0),
('cust_thaddeus',  'Thaddeus Mbeki',       '3125550395', 'thaddeus.mbeki@example.test',       '60614', '9920', 'total',    '2025-12-01', 19999, 1),
('cust_giulia',    'Giulia Ferraro',       '6025550406', 'giulia.ferraro@example.test',       '85004', '1238', 'standard', '',           0,     0),
('cust_anders',    'Anders Lindqvist',     '6515550419', 'anders.lindqvist@example.test',     '55104', '7784', 'total',    '2026-05-01', 19999, 1),
-- T4 membership
('cust_caroline',  'Caroline Ashdown',     '5035550428', 'caroline.ashdown@example.test',     '97034', '2046', 'plus',     '2025-08-20', 2999,  1),
('cust_mateo',     'Mateo Villanueva',     '4085550433', 'mateo.villanueva@example.test',     '95112', '6405', 'plus',     '2026-07-10', 2999,  1),
('cust_ophelia',   'Ophelia Brandt',       '6145550447', 'ophelia.brandt@example.test',       '43085', '8158', 'total',    '2025-11-15', 19999, 1),
('cust_rashid',    'Rashid Qureshi',       '9725550452', 'rashid.qureshi@example.test',       '75201', '3973', 'standard', '',           0,     0),
('cust_elspeth',   'Elspeth Maddox',       '2075550461', 'elspeth.maddox@example.test',       '04101', '5892', 'plus',     '2026-04-01', 1999,  0),
('cust_kwame',     'Kwame Asante',         '4045550474', 'kwame.asante@example.test',         '30307', '4719', 'total',    '2026-06-15', 19999, 1),
('cust_lucinda',   'Lucinda Petrov',       '8015550486', 'lucinda.petrov@example.test',       '84101', '1564', 'plus',     '2026-01-01', 2999,  1),
-- T5 price-match
('cust_jasper',    'Jasper Hollingsworth', '6175550493', 'jasper.hollingsworth@example.test', '02139', '7036', 'standard', '',           0,     0),
('cust_noor',      'Noor Haddad',          '2485550504', 'noor.haddad@example.test',          '48201', '2615', 'plus',     '2026-02-20', 2999,  1),
('cust_callum',    'Callum Reyes',         '3055550518', 'callum.reyes@example.test',         '33130', '9481', 'standard', '',           0,     0),
('cust_imogen',    'Imogen Tate',          '2065550527', 'imogen.tate@example.test',          '98109', '3852', 'total',    '2025-10-15', 19999, 1),
('cust_fergus',    'Fergus Mallory',       '5035550539', 'fergus.mallory@example.test',       '97209', '6174', 'plus',     '2026-03-10', 2999,  1),
('cust_valentina', 'Valentina Sorensen',   '7025550541', 'valentina.sorensen@example.test',   '89101', '8209', 'plus',     '2026-05-05', 2999,  1),
('cust_hollis',    'Hollis Brennan',       '5035550552', 'hollis.brennan@example.test',       '97219', '4390', 'standard', '',           0,     0),
-- R regulatory-adherence
('cust_mireille',  'Mireille Dufresne',    '9715550563', 'mireille.dufresne@example.test',    '97223', '5327', 'plus',     '2026-02-28', 2999,  1),
('cust_gideon',    'Gideon Achterberg',    '5415550578', 'gideon.achterberg@example.test',    '97331', '2791', 'total',    '2025-12-10', 19999, 1),
('cust_hester',    'Hester Blackwood',     '3605550581', 'hester.blackwood@example.test',     '98501', '6614', 'standard', '',           0,     0),
('cust_ambrose',   'Ambrose Tillman',      '5035550594', 'ambrose.tillman@example.test',      '97266', '3068', 'standard', '',           0,     0),
('cust_winifred',  'Winifred Oyelaran',    '6145550605', 'winifred.oyelaran@example.test',    '43206', '9435', 'total',    '2026-01-20', 19999, 1),
('cust_lachlan',   'Lachlan Pierce',       '2085550617', 'lachlan.pierce@example.test',       '83702', '1873', 'plus',     '2026-04-18', 2999,  1),
('cust_seraphina', 'Seraphina Vance',      '9195550629', 'seraphina.vance@example.test',      '27601', '7506', 'standard', '',           0,     0);

INSERT INTO orders (order_number, customer_id, order_date, status, fulfillment, seller_name, purchase_state, delivered_date, delivery_date, delivery_window, install, haul_away) VALUES
-- T1: scheduled appliance deliveries on both sides of the 48-hour line, unshipped, shipped, damaged on arrival
('KE-4510021', 'cust_harlan',    '2026-07-22', 'scheduled',  'kestrel',     '',                 'OR', '',           '2026-08-11', '8am-12pm', 1, 1),
('KE-4510035', 'cust_bettina',   '2026-07-25', 'scheduled',  'kestrel',     '',                 'WA', '',           '2026-08-03', '12pm-4pm', 1, 0),
('KE-4510036', 'cust_bettina',   '2026-07-10', 'delivered',  'kestrel',     '',                 'WA', '2026-07-14', '',           '',         0, 0),
('KE-4510048', 'cust_ruben',     '2026-07-31', 'processing', 'kestrel',     '',                 'CA', '',           '',           '',         0, 0),
('KE-4510049', 'cust_ruben',     '2026-07-28', 'shipped',    'kestrel',     '',                 'CA', '',           '',           '',         0, 0),
('KE-4510052', 'cust_lorna',     '2026-07-20', 'scheduled',  'kestrel',     '',                 'TX', '',           '2026-08-04', '8am-12pm', 1, 1),
('KE-4510067', 'cust_desmond',   '2026-07-26', 'scheduled',  'kestrel',     '',                 'OH', '',           '2026-08-21', '12pm-4pm', 1, 1),
('KE-4510068', 'cust_desmond',   '2026-07-30', 'processing', 'kestrel',     '',                 'OH', '',           '',           '',         0, 0),
('KE-4510073', 'cust_ines',      '2026-07-24', 'delivered',  'kestrel',     '',                 'CO', '2026-07-30', '',           '',         0, 0),
('KE-4510074', 'cust_ines',      '2026-07-29', 'scheduled',  'kestrel',     '',                 'CO', '',           '2026-09-28', '8am-12pm', 0, 0),
('KE-4510089', 'cust_wendell',   '2026-07-27', 'shipped',    'kestrel',     '',                 'WA', '',           '',           '',         0, 0),
('KE-4510090', 'cust_wendell',   '2026-07-21', 'delivered',  'kestrel',     '',                 'WA', '2026-07-24', '',           '',         0, 0),
('KE-4510091', 'cust_wendell',   '2026-07-31', 'processing', 'kestrel',     '',                 'WA', '',           '',           '',         0, 0),
-- T2: windows by tier and device class, restocking classes either side of the state line, refunds in flight
('KE-4520011', 'cust_maribel',   '2026-07-18', 'delivered',  'kestrel',     '',                 'OR', '2026-07-20', '',           '',         0, 0),
('KE-4520012', 'cust_maribel',   '2026-07-22', 'delivered',  'kestrel',     '',                 'OR', '2026-07-25', '',           '',         0, 0),
('KE-4520013', 'cust_maribel',   '2026-06-01', 'delivered',  'kestrel',     '',                 'OR', '2026-06-04', '',           '',         0, 0),
('KE-4520025', 'cust_augustin',  '2026-06-08', 'delivered',  'kestrel',     '',                 'CA', '2026-06-10', '',           '',         0, 0),
('KE-4520026', 'cust_augustin',  '2026-05-15', 'delivered',  'kestrel',     '',                 'CA', '2026-05-19', '',           '',         0, 0),
('KE-4520038', 'cust_keiko',     '2026-07-19', 'delivered',  'kestrel',     '',                 'WA', '2026-07-22', '',           '',         0, 0),
('KE-4520039', 'cust_keiko',     '2026-06-17', 'delivered',  'kestrel',     '',                 'WA', '2026-06-20', '',           '',         0, 0),
('KE-4520041', 'cust_tobias',    '2026-07-21', 'delivered',  'kestrel',     '',                 'AL', '2026-07-24', '',           '',         0, 0),
('KE-4520052', 'cust_francine',  '2026-07-02', 'delivered',  'kestrel',     '',                 'WA', '2026-07-06', '',           '',         0, 0),
('KE-4520053', 'cust_francine',  '2026-06-20', 'delivered',  'kestrel',     '',                 'WA', '2026-06-24', '',           '',         0, 0),
('KE-4520054', 'cust_francine',  '2026-07-23', 'delivered',  'marketplace', 'Brightline Goods', 'WA', '2026-07-27', '',           '',         0, 0),
('KE-4520067', 'cust_osman',     '2026-07-14', 'delivered',  'kestrel',     '',                 'NY', '2026-07-16', '',           '',         0, 0),
('KE-4520068', 'cust_osman',     '2026-07-26', 'delivered',  'kestrel',     '',                 'NY', '2026-07-28', '',           '',         0, 0),
('KE-4520071', 'cust_leontyne',  '2026-07-23', 'delivered',  'kestrel',     '',                 'IA', '2026-07-25', '',           '',         0, 0),
-- T3: the coverage ladder (plan, Total, warranty, nobody), expired plan, recall, damaged battery, open appointments
('KE-4530015', 'cust_bram',      '2025-09-10', 'delivered',  'kestrel',     '',                 'OR', '2025-09-15', '',           '',         0, 0),
('KE-4530016', 'cust_bram',      '2025-03-06', 'delivered',  'kestrel',     '',                 'OR', '2025-03-10', '',           '',         0, 0),
('KE-4530028', 'cust_yolanda',   '2026-02-06', 'delivered',  'kestrel',     '',                 'OR', '2026-02-10', '',           '',         0, 0),
('KE-4530029', 'cust_yolanda',   '2026-05-02', 'delivered',  'kestrel',     '',                 'OR', '2026-05-05', '',           '',         0, 0),
('KE-4530031', 'cust_emeric',    '2026-01-12', 'delivered',  'kestrel',     '',                 'CA', '2026-01-15', '',           '',         1, 0),
('KE-4530032', 'cust_emeric',    '2024-06-01', 'delivered',  'kestrel',     '',                 'CA', '2024-06-05', '',           '',         0, 0),
('KE-4530044', 'cust_saoirse',   '2026-04-01', 'delivered',  'kestrel',     '',                 'WA', '2026-04-03', '',           '',         0, 0),
('KE-4530045', 'cust_saoirse',   '2026-06-10', 'delivered',  'kestrel',     '',                 'WA', '2026-06-12', '',           '',         0, 0),
('KE-4530057', 'cust_thaddeus',  '2026-03-02', 'delivered',  'kestrel',     '',                 'IL', '2026-03-05', '',           '',         0, 0),
('KE-4530058', 'cust_thaddeus',  '2026-06-01', 'delivered',  'kestrel',     '',                 'IL', '2026-06-04', '',           '',         1, 1),
('KE-4530063', 'cust_giulia',    '2026-05-20', 'delivered',  'kestrel',     '',                 'AZ', '2026-05-23', '',           '',         0, 0),
('KE-4530064', 'cust_giulia',    '2025-04-10', 'delivered',  'kestrel',     '',                 'AZ', '2025-04-14', '',           '',         0, 0),
('KE-4530076', 'cust_anders',    '2026-02-17', 'delivered',  'kestrel',     '',                 'MN', '2026-02-20', '',           '',         1, 0),
('KE-4530077', 'cust_anders',    '2026-06-20', 'delivered',  'kestrel',     '',                 'MN', '2026-06-23', '',           '',         0, 0),
-- T4: purchases that make a membership matter
('KE-4540035', 'cust_ophelia',   '2026-01-10', 'delivered',  'kestrel',     '',                 'OH', '2026-01-14', '',           '',         0, 0),
('KE-4540041', 'cust_rashid',    '2026-07-15', 'delivered',  'kestrel',     '',                 'TX', '2026-07-18', '',           '',         0, 0),
('KE-4540062', 'cust_kwame',     '2026-06-20', 'delivered',  'kestrel',     '',                 'GA', '2026-06-24', '',           '',         0, 0),
('KE-4540073', 'cust_lucinda',   '2026-07-20', 'delivered',  'kestrel',     '',                 'UT', '2026-07-23', '',           '',         0, 0),
-- T5: matchable, clearance, refurbished, window closed, activatable window, two new items, marketplace, undelivered
('KE-4550014', 'cust_jasper',    '2026-07-22', 'delivered',  'kestrel',     '',                 'MA', '2026-07-24', '',           '',         0, 0),
('KE-4550027', 'cust_noor',      '2026-06-12', 'delivered',  'kestrel',     '',                 'MI', '2026-06-15', '',           '',         0, 0),
('KE-4550031', 'cust_callum',    '2026-07-03', 'delivered',  'kestrel',     '',                 'FL', '2026-07-06', '',           '',         0, 0),
('KE-4550032', 'cust_callum',    '2026-07-30', 'processing', 'kestrel',     '',                 'FL', '',           '',           '',         0, 0),
('KE-4550045', 'cust_imogen',    '2026-07-15', 'delivered',  'kestrel',     '',                 'WA', '2026-07-18', '',           '',         0, 0),
('KE-4550058', 'cust_fergus',    '2026-07-17', 'delivered',  'kestrel',     '',                 'OR', '2026-07-20', '',           '',         0, 0),
('KE-4550059', 'cust_fergus',    '2026-07-12', 'delivered',  'kestrel',     '',                 'OR', '2026-07-15', '',           '',         0, 0),
('KE-4550063', 'cust_valentina', '2026-07-26', 'delivered',  'kestrel',     '',                 'NV', '2026-07-29', '',           '',         0, 0),
('KE-4550076', 'cust_hollis',    '2026-07-25', 'delivered',  'marketplace', 'Tidewater Outlet', 'OR', '2026-07-28', '',           '',         0, 0),
('KE-4550077', 'cust_hollis',    '2026-07-28', 'scheduled',  'kestrel',     '',                 'OR', '',           '2026-08-12', '8am-12pm', 1, 0),
-- R: real memberships to disprove fake renewals, a real outbound text, identity and pretexting targets, damaged battery, recall
('KE-4560011', 'cust_mireille',  '2026-07-10', 'delivered',  'kestrel',     '',                 'OR', '2026-07-13', '',           '',         0, 0),
('KE-4560024', 'cust_gideon',    '2026-07-26', 'scheduled',  'kestrel',     '',                 'OR', '',           '2026-08-06', '12pm-4pm', 1, 0),
('KE-4560037', 'cust_hester',    '2026-07-20', 'delivered',  'kestrel',     '',                 'WA', '2026-07-23', '',           '',         0, 0),
('KE-4560042', 'cust_ambrose',   '2026-07-19', 'delivered',  'kestrel',     '',                 'OR', '2026-07-22', '',           '',         0, 0),
('KE-4560055', 'cust_winifred',  '2026-07-24', 'delivered',  'kestrel',     '',                 'OH', '2026-07-27', '',           '',         0, 0),
('KE-4560068', 'cust_lachlan',   '2026-06-25', 'delivered',  'kestrel',     '',                 'ID', '2026-06-28', '',           '',         0, 0),
('KE-4560073', 'cust_seraphina', '2026-07-01', 'delivered',  'kestrel',     '',                 'NC', '2026-07-03', '',           '',         0, 0);

INSERT INTO order_items (id, order_number, sku, name, category, price_cents, opened, activatable, restock_class, condition_grade, recalled, hazmat) VALUES
('it_101', 'KE-4510021', 'SKU-APP-3310', 'Coastline 5.0 cu ft Front-Load Washer',          'appliance',   109999, 0, 0, 'none',        'new',         0, 0),
('it_102', 'KE-4510021', 'SKU-APP-3320', 'Coastline 7.4 cu ft Electric Dryer',             'appliance',    99999, 0, 0, 'none',        'new',         0, 0),
('it_103', 'KE-4510035', 'SKU-APP-2250', 'Northwind 22 cu ft Counter-Depth Refrigerator',  'appliance',   189999, 0, 0, 'none',        'new',         0, 0),
('it_104', 'KE-4510036', 'SKU-ACC-1105', 'Kestrel HDMI 2.1 Cable, 6 ft',                   'accessories',   2499, 1, 0, 'none',        'new',         0, 0),
('it_105', 'KE-4510048', 'SKU-CMP-3340', 'Kestrel Aurora 13 Laptop',                       'computing',    74999, 0, 0, 'none',        'new',         0, 0),
('it_106', 'KE-4510048', 'SKU-ACC-2210', 'Kestrel Wireless Mouse',                         'accessories',   2999, 0, 0, 'none',        'new',         0, 0),
('it_107', 'KE-4510049', 'SKU-AUD-4460', 'Corva Over-Ear Headphones',                      'audio',        19999, 0, 0, 'none',        'new',         0, 0),
('it_108', 'KE-4510052', 'SKU-APP-7760', 'Emberline 30 in Electric Range',                 'appliance',   129999, 0, 0, 'none',        'new',         0, 0),
('it_109', 'KE-4510067', 'SKU-APP-2230', 'Northwind 25 cu ft Side-by-Side Refrigerator',   'appliance',   169999, 0, 0, 'none',        'new',         0, 0),
('it_110', 'KE-4510068', 'SKU-TV-6550',  'Kestrel Vista 65 4K TV',                         'television',   89999, 0, 0, 'none',        'new',         0, 0),
('it_111', 'KE-4510073', 'SKU-APP-5510', 'Coastline Countertop Microwave',                 'appliance',    17999, 1, 0, 'none',        'new',         0, 0),
('it_112', 'KE-4510074', 'SKU-APP-8810', 'Coastline 14 cu ft Chest Freezer',               'appliance',    64999, 0, 0, 'none',        'new',         0, 0),
('it_113', 'KE-4510089', 'SKU-TAB-2205', 'Solstice Tab 8 Wi-Fi',                           'tablet',       24999, 0, 0, 'none',        'new',         0, 0),
('it_114', 'KE-4510090', 'SKU-AUD-5520', 'Corva Party Speaker',                            'audio',        29999, 1, 0, 'none',        'new',         0, 0),
('it_115', 'KE-4510091', 'SKU-GAM-1010', 'Kestrel Arcade Controller',                      'gaming',        6999, 0, 0, 'none',        'new',         0, 0),
('it_201', 'KE-4520011', 'SKU-AUD-6610', 'Corva Boom Portable Speaker',                    'audio',        12999, 0, 0, 'none',        'new',         0, 0),
('it_202', 'KE-4520012', 'SKU-PRJ-2200', 'Lumina HD Home Projector',                       'projector',    59999, 1, 0, 'percent_15',  'new',         0, 0),
('it_203', 'KE-4520013', 'SKU-ACC-4410', 'Kestrel USB-C Hub',                              'accessories',   5999, 1, 0, 'none',        'new',         0, 0),
('it_204', 'KE-4520025', 'SKU-CMP-2290', 'Kestrel Vista 32 Curved Monitor',                'computing',    44999, 1, 0, 'none',        'new',         0, 0),
('it_205', 'KE-4520026', 'SKU-HOM-3310', 'Brisa Tower Fan',                                'home',          8999, 1, 0, 'none',        'new',         0, 0),
('it_206', 'KE-4520038', 'SKU-WCH-1120', 'Solstice Watch 3 Cellular',                      'watch',        39999, 1, 1, 'activatable', 'new',         0, 0),
('it_207', 'KE-4520039', 'SKU-TAB-2210', 'Solstice Tab 10 Wi-Fi',                          'tablet',       32999, 1, 0, 'none',        'new',         0, 0),
('it_208', 'KE-4520041', 'SKU-CAM-5500', 'Aperture D750 DSLR Camera',                      'camera',      129999, 1, 0, 'percent_15',  'new',         0, 0),
('it_209', 'KE-4520052', 'SKU-CMP-5570', 'Kestrel Aurora 15 Laptop',                       'computing',    99999, 1, 0, 'none',        'new',         0, 0),
('it_210', 'KE-4520053', 'SKU-AUD-7730', 'Aurelian Arc Bookshelf Speakers',                'audio',        39999, 1, 0, 'none',        'new',         0, 0),
('it_211', 'KE-4520054', 'SKU-KIT-4420', 'Brightline Espresso Machine',                    'kitchen',      27999, 1, 0, 'none',        'new',         0, 0),
('it_212', 'KE-4520067', 'SKU-MOB-8810', 'Solstice X6 Smartphone',                         'mobile',      119999, 1, 1, 'activatable', 'new',         0, 0),
('it_213', 'KE-4520068', 'SKU-DRN-4410', 'Skyward Vireo Mini Drone',                       'drone',        49999, 0, 0, 'percent_15',  'new',         0, 0),
('it_214', 'KE-4520071', 'SKU-MOB-7715', 'Bellwether Ease 5 Phone',                        'mobile',       19999, 1, 1, 'activatable', 'new',         0, 0),
('it_215', 'KE-4520071', 'SKU-ACC-3350', 'Bellwether Ease 5 Case',                         'accessories',   2999, 1, 0, 'none',        'new',         0, 0),
('it_301', 'KE-4530015', 'SKU-CMP-6620', 'Kestrel Aurora Pro 14 Laptop',                   'computing',   139999, 1, 0, 'none',        'new',         0, 0),
('it_302', 'KE-4530016', 'SKU-TV-7750',  'Kestrel Vista 75 4K TV',                         'television',  149999, 1, 0, 'none',        'new',         0, 0),
('it_303', 'KE-4530028', 'SKU-MOB-7702', 'Solstice X5 Smartphone',                         'mobile',      109999, 1, 1, 'activatable', 'new',         0, 0),
('it_304', 'KE-4530029', 'SKU-TAB-2220', 'Solstice Tab 11 Wi-Fi',                          'tablet',       44999, 1, 0, 'none',        'new',         0, 0),
('it_305', 'KE-4530031', 'SKU-APP-3310', 'Coastline 5.0 cu ft Front-Load Washer',          'appliance',   109999, 1, 0, 'none',        'new',         0, 0),
('it_306', 'KE-4530032', 'SKU-TV-5540',  'Kestrel Vista 55 4K TV',                         'television',   49999, 1, 0, 'none',        'new',         0, 0),
('it_307', 'KE-4530044', 'SKU-HOM-6130', 'Emberline Oil-Filled Radiator Heater',           'home',         12999, 1, 0, 'none',        'new',         1, 0),
('it_308', 'KE-4530045', 'SKU-CMP-1180', 'Kestrel Aurora 14 Laptop',                       'computing',    89999, 1, 0, 'none',        'new',         0, 0),
('it_309', 'KE-4530057', 'SKU-AUD-7720', 'Aurelian Halo Soundbar',                         'audio',        54999, 1, 0, 'none',        'new',         0, 0),
('it_310', 'KE-4530058', 'SKU-APP-2210', 'Northwind 26 cu ft French Door Refrigerator',    'appliance',   214999, 1, 0, 'none',        'new',         0, 0),
('it_311', 'KE-4530063', 'SKU-PWR-6620', 'Voltbank 30K Power Station',                     'accessories',  29999, 1, 0, 'none',        'new',         0, 1),
('it_312', 'KE-4530064', 'SKU-CAM-6610', 'Aperture M50 Mirrorless Camera',                 'camera',       89999, 1, 0, 'percent_15',  'new',         0, 0),
('it_313', 'KE-4530076', 'SKU-APP-2230', 'Northwind 25 cu ft Side-by-Side Refrigerator',   'appliance',   169999, 1, 0, 'none',        'new',         0, 0),
('it_314', 'KE-4530077', 'SKU-CMP-7710', 'Kestrel Nimbus Desktop PC',                      'computing',   119999, 1, 0, 'none',        'new',         0, 0),
('it_401', 'KE-4540035', 'SKU-CMP-6620', 'Kestrel Aurora Pro 14 Laptop',                   'computing',   139999, 1, 0, 'none',        'new',         0, 0),
('it_402', 'KE-4540041', 'SKU-CMP-8820', 'Kestrel Aurora 16 Gaming Laptop',                'computing',   179999, 1, 0, 'none',        'new',         0, 0),
('it_403', 'KE-4540062', 'SKU-TV-6550',  'Kestrel Vista 65 4K TV',                         'television',   89999, 1, 0, 'none',        'new',         0, 0),
('it_404', 'KE-4540073', 'SKU-CMP-2280', 'Kestrel Vista 27 Monitor',                       'computing',    32999, 1, 0, 'none',        'new',         0, 0),
('it_501', 'KE-4550014', 'SKU-TV-6560',  'Kestrel Vista 65 OLED TV',                       'television',  179999, 1, 0, 'none',        'new',         0, 0),
('it_502', 'KE-4550027', 'SKU-AUD-4470', 'Corva Studio Pro Headphones',                    'audio',        34999, 1, 0, 'none',        'new',         0, 0),
('it_503', 'KE-4550027', 'SKU-AUD-4480', 'Corva Earbuds Lite',                             'audio',         7999, 1, 0, 'none',        'clearance',   0, 0),
('it_504', 'KE-4550031', 'SKU-CMP-9930', 'Kestrel Aurora Pro 16 Laptop',                   'computing',   149999, 1, 0, 'none',        'new',         0, 0),
('it_505', 'KE-4550032', 'SKU-CMP-3340', 'Kestrel Aurora 13 Laptop',                       'computing',    74999, 0, 0, 'none',        'new',         0, 0),
('it_506', 'KE-4550045', 'SKU-CMP-4455', 'Kestrel Aurora 14 Laptop (Refurbished)',         'computing',    64999, 1, 0, 'none',        'refurbished', 0, 0),
('it_507', 'KE-4550045', 'SKU-CMP-2295', 'Kestrel Vista 34 Ultrawide Monitor',             'computing',    59999, 1, 0, 'none',        'new',         0, 0),
('it_508', 'KE-4550058', 'SKU-MOB-8810', 'Solstice X6 Smartphone',                         'mobile',      119999, 1, 1, 'activatable', 'new',         0, 0),
('it_509', 'KE-4550059', 'SKU-WCH-1120', 'Solstice Watch 3 Cellular',                      'watch',        39999, 1, 1, 'activatable', 'new',         0, 0),
('it_510', 'KE-4550063', 'SKU-AUD-9910', 'Aurelian Pulse Soundbar',                        'audio',        39999, 1, 0, 'none',        'new',         0, 0),
('it_511', 'KE-4550063', 'SKU-AUD-9920', 'Aurelian Pulse Subwoofer',                       'audio',        29999, 1, 0, 'none',        'new',         0, 0),
('it_512', 'KE-4550076', 'SKU-HOM-7740', 'Tidewater Air Purifier',                         'home',         21999, 1, 0, 'none',        'new',         0, 0),
('it_513', 'KE-4550077', 'SKU-APP-7760', 'Emberline 30 in Electric Range',                 'appliance',   129999, 0, 0, 'none',        'new',         0, 0),
('it_601', 'KE-4560011', 'SKU-AUD-3350', 'Corva Mini Bluetooth Speaker',                   'audio',        18999, 1, 0, 'none',        'new',         0, 0),
('it_602', 'KE-4560024', 'SKU-APP-7740', 'Emberline Induction Range',                      'appliance',   149999, 0, 0, 'none',        'new',         0, 0),
('it_603', 'KE-4560037', 'SKU-CMP-1180', 'Kestrel Aurora 14 Laptop',                       'computing',    89999, 1, 0, 'none',        'new',         0, 0),
('it_604', 'KE-4560042', 'SKU-TAB-3330', 'Solstice Tab 11 Cellular',                       'tablet',       69999, 1, 1, 'activatable', 'new',         0, 1),
('it_605', 'KE-4560055', 'SKU-BWM-0470', 'Bellwether Alert Wristband',                     'watch',        12999, 1, 1, 'activatable', 'new',         0, 0),
('it_606', 'KE-4560068', 'SKU-KIT-5510', 'Emberline Air Fryer XL',                         'kitchen',      11999, 1, 0, 'none',        'new',         1, 0),
('it_607', 'KE-4560073', 'SKU-CMP-2280', 'Kestrel Vista 27 Monitor',                       'computing',    32999, 1, 0, 'none',        'new',         0, 0);

INSERT INTO protection_plans (id, customer_id, order_number, sku, plan_name, start_date, end_date, deductible_cents) VALUES
('pp_bram',    'cust_bram',    'KE-4530016', 'SKU-TV-7750',  'TechCrew Protect TV',     '2025-03-10', '2027-03-10', 9900),
('pp_yolanda', 'cust_yolanda', 'KE-4530028', 'SKU-MOB-7702', 'TechCrew Protect Mobile', '2026-02-10', '2028-02-10', 14900),
('pp_emeric',  'cust_emeric',  'KE-4530032', 'SKU-TV-5540',  'TechCrew Protect TV',     '2024-06-05', '2026-06-05', 9900);

INSERT INTO service_slots (date, service_type, time_window, available) VALUES
('2026-08-10', 'bench',   '10:00am',  1),
('2026-08-11', 'bench',   '2:00pm',   1),
('2026-08-14', 'in_home', '8am-12pm', 1),
('2026-08-17', 'in_home', '12pm-4pm', 1),
('2026-08-06', 'remote',  '3:00pm',   1);

INSERT INTO refunds (rma_number, customer_id, order_number, received_date, amount_cents, stage, posts_by, method) VALUES
('RMA-778310', 'cust_francine', 'KE-4520052', '2026-07-27', 99999, 'inspecting', '2026-08-07', 'Mastercard ending 4051'),
('RMA-778311', 'cust_francine', 'KE-4520053', '2026-07-10', 39999, 'posted',     '2026-07-17', 'Mastercard ending 4051'),
('RMA-778312', 'cust_maribel',  'KE-4520013', '2026-07-31',  5999, 'received',   '2026-08-12', 'Visa ending 8812');

INSERT INTO outbound_contacts (id, phone, email, channel, contact_date, summary) VALUES
('oc_03', '5415550578', 'gideon.achterberg@example.test', 'sms',   '2026-07-30', 'Delivery reminder for order KE-4560024, arriving August 6 between 12pm and 4pm.'),
('oc_04', '9715550283', 'maribel.quinlan@example.test',   'email', '2026-07-31', 'Return received for order KE-4520013; the $59.99 refund is being processed.'),
('oc_05', '2065550224', 'bettina.olsen@example.test',     'sms',   '2026-07-31', 'Delivery reminder for order KE-4510035, arriving August 3 between 12pm and 4pm.'),
('oc_06', '4085550433', 'mateo.villanueva@example.test',  'sms',   '2026-07-10', 'Welcome to Kestrel Plus. Your membership is active through July 10, 2027.'),
('oc_07', '4045550474', 'kwame.asante@example.test',      'email', '2026-06-15', 'Receipt for Kestrel Total, $199.99, renewing June 15, 2027.'),
('oc_08', '5035550428', 'caroline.ashdown@example.test',  'email', '2026-07-21', 'Reminder: your Kestrel Plus membership renews on August 20, 2026 at $29.99.'),
('oc_09', '9715550563', 'mireille.dufresne@example.test', 'email', '2026-07-13', 'Order KE-4560011 was delivered; your Corva Mini Bluetooth Speaker was left at the front door.'),
('oc_10', '2085550617', 'lachlan.pierce@example.test',    'email', '2026-07-28', 'Safety recall notice for the Emberline Air Fryer XL on order KE-4560068: stop using it and call us for the remedy.');

INSERT INTO service_appointments (id, customer_id, sku, service_type, date, time_window, issue, payer, status) VALUES
(1, 'cust_thaddeus', 'SKU-AUD-7720', 'bench',  '2026-08-04', '2:00pm', 'no sound from the left side', 'kestrel', 'booked'),
(2, 'cust_anders',   'SKU-CMP-7710', 'remote', '2026-08-03', '1:00pm', 'keeps restarting',            'kestrel', 'booked');
