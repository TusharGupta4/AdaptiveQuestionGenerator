# (q, sub, marks, chapter, text, img)  -- ICSE 2025 (Oswaal solved paper), paper_no = 1
M25="Study the extract of the Survey of India Map Sheet No. G43S10 and answer the following questions: "
O="On the outline map of India provided: "
MAP="Map Work (Survey of India)"; IND="Map of India"
CL="Climate of India"; SO="Soil Resources of India"; NV="Natural Vegetation of India"; WR="Water Resources"
ME="Minerals and Energy Resources"; AG="Agriculture in India"; IN="Manufacturing Industries"; TR="Transport"; WM="Waste Management"
P25=[
(1,"i",2,MAP,M25+"(a) Give the six-figure grid reference for spot height .437 in the southeastern part of the map extract. (b) Aman, a local craftsman, wants to sell his product to a large gathering to earn money instantly. 1. Which settlement should he go to? 2. Name the month in which he should visit the settlement named by you above.","map"),
(1,"ii",2,MAP,M25+"(a) On which bank of the Sukli nadi is the settlement of Pamera situated? (b) Identify the settlement pattern seen in the grid square 6732.","map"),
(1,"iii",2,MAP,M25+"Roshan, while travelling from Sirori to Tokra, observed that the surface water sources are dry except for the reservoir near Tokra. (a) What according to you may be the reason for the presence of water in the reservoir in 6832 near Tokra settlement? (b) State whether this reservoir is artificial or natural source of water.","map"),
(1,"iv",2,MAP,M25+"(a) What is the direct distance between Gulabganj to Pithapura? Give your answer in kilometre. (b) Mention the compass direction of Pithapura from Gulabganj.","map"),
(1,"v",2,MAP,M25+"(a) Name two man-made features seen in the grid square 6534. (b) Define contour interval.","map"),
]
for s,t in [("i","Mark and label the Nathu-La pass."),("ii","Shade and name the coastal plain that occupies a large part of Kerala."),("iii","Mark and label Digboi."),("iv","Mark and label Chilka lake."),("v","Mark with arrows and name the wind that brings rainfall to Tamil Nadu coast during winter."),("vi","Mark and label the river Sutlej."),("vii","Mark and label the Standard Meridian of India."),("viii","Mark and label Satpura range."),("ix","Shade and label the Chota Nagpur plateau."),("x","Mark and label Visakhapatnam.")]:
    P25.append((2,s,1,IND,O+t,"india"))
C="Choose the correct answers to the questions from the given options. (Do not copy the questions, write the correct answers only.) "
P25+=[
(3,"i",1,CL,C+"Assertion(A): Mumbai receives more rainfall than Pune. Reason(R): Mumbai gets rain from Arabian Sea branch of southwest monsoon. (a) Both (A) and (R) are true and (R) is the correct explanation for (A). (b) Both (A) and (R) are true and (R) is not the correct explanation for (A). (c) (A) is true and (R) is false. (d) (A) is false and (R) is true.",""),
(3,"ii",1,SO,C+"Which of the following pairs of soils displays similar characteristics in terms of their colour and texture? (a) Alluvial soil and laterite soil (b) Black soil and red soil (c) Red soil and laterite soil (d) Alluvial soil and black soil",""),
(3,"iii",1,NV,C+"The type of natural vegetation shown in the picture given below is found in: (a) Tropical desert (b) Tropical deciduous (c) Tropical evergreen (d) Littoral forest","trees25"),
(3,"iv",1,WR,C+"Which of the following prevents wastage of water? (a) Canal (b) Well (c) Sprinkler (d) Tube well",""),
(3,"v",1,ME,C+"Balaghat: Manganese:: Mumbai High: ____________ (a) Copper (b) Coal (c) Iron Ore (d) Petroleum",""),
(3,"vi",1,AG,C+"A microbiological process that loosens the bark of a crop and facilitates removal of fibre from the stalk: (a) Rolling (b) Ratooning (c) Retting (d) Fermentation",""),
(3,"vii",1,IN,C+"Which industry amongst the following has revolutionised the lifestyle of the Indian masses in recent years? (a) Cotton Textile (b) Electronic (c) Iron and Steel (d) Sugar",""),
(3,"viii",1,IN,C+"Which of the following household products is associated with the petrochemical industry? (a) Glass bottle (b) Wooden chopping board (c) Kitchen knife (d) Plastic mug",""),
(3,"ix",1,TR,C+"Raman, a dairy farmer in Ludhiana, supplies milk within the city on a daily basis. Which mode of transport is he most likely to use? (a) Railway (b) Roadway (c) Airway (d) Waterway",""),
(3,"x",1,WM,C+"The collection of discarded materials and converting them into useful products is: (a) Recycling (b) Processing (c) Reducing (d) Composting",""),
(4,"i",2,CL,"'Severe cyclonic storms are often formed over the Bay of Bengal during the retreating monsoon season'. (a) Name two states that are affected by tropical cyclones on the eastern coast of India. (b) The temperate cyclones cause less damage than the tropical cyclones. Give any two points to support this statement.",""),
(4,"ii",2,CL,"(a) Name the local wind that causes rainfall in the states of Assam and West Bengal in the month of April. (b) How is this rainfall beneficial for the states mentioned above?",""),
(4,"iii",3,CL,"With reference to Figure A and Figure B given below, answer the questions that follow: (a) Name the winds shown by arrows in Figure A and Figure B. (b) How is the wind shown in Figure A different from the one shown in Figure B?","winds25"),
(4,"iv",3,CL,"Study the climate data of station X and answer the following questions: Month: Jan Feb Mar Apr May June July Aug Sep Oct Nov Dec | Temp (°C): 24.0 25.4 26.7 28.3 30.0 28.9 27.6 27.4 27.3 27.1 27.0 25.0 | Rainfall (cm): 0.25 0.25 - - 1.75 50.2 61.0 37.0 27.0 4.75 1.50 - (a) What is the annual range of temperature for station X? (b) Which is the wettest month? (c) Name the wind which brings rainfall for station X during the rainy season.",""),
(5,"i",2,SO,"The Ganga Plain is known for its fertile soil. It is often referred to as the food bowl of India. This region supports a variety of crops such as rice, wheat, pulses, jute and sugarcane. (a) Name the soil that is found in large parts of Ganga plain. (b) Give two properties of this soil which helps it to produce a variety of crops.",""),
(5,"ii",2,SO,"(a) What is meant by soil erosion? (b) Name any two agents of soil erosion.",""),
(5,"iii",3,SO,"Give a geographical reason to explain each of the following: (a) Soil conservation is the need of the hour. (b) Red soil has a poor water retention capacity. (c) Laterite soils are infertile.",""),
(5,"iv",3,SO,"With reference to black soil of India, answer the following questions. (a) How is this soil formed? (b) How is this soil able to retain moisture for a long period? (c) Mention any two minerals present in this soil.",""),
(6,"i",2,NV,"India has lost 2.33 million hectares of tree cover since the year 2000. This is equivalent to a six per cent decrease in tree cover during this period. (Source: The Indian Express, 12.04.2024) (a) Mention any two causes of the decrease in the forest cover of India. (b) Name a conservation method that may be used to help in increasing the forest cover.",""),
(6,"ii",2,NV,"Mention the climatic condition suitable for the development of tropical evergreen forest.",""),
(6,"iii",3,NV,"State any three differences between tropical deciduous and tropical desert vegetation.",""),
(6,"iv",3,NV,"(a) Give any two reasons for the great diversity of natural vegetation in India. (b) How do the forests help in maintenance of air quality?",""),
(7,"i",2,WR,"Mention any one advantage and any one disadvantage of well irrigation.",""),
(7,"ii",2,WR,"Suggest any two measures to overcome scarcity of water in the metropolitan cities of India.",""),
(7,"iii",3,WR,"Give one reason to explain each of the following: (a) Tank irrigation is NOT common in Northern India. (b) Canal irrigation is important in Punjab. (c) All farmers do not use tube well irrigation even if the geographical condition is favourable.",""),
(7,"iv",3,WR,"State any three objectives of rainwater harvesting.",""),
(8,"i",2,ME,"With the rising price of fossil fuel every passing day, it is very important to develop non-conventional energy resource. (Bulletin - Department of non-conventional sources of energy) (a) Name a non-conventional energy source that can be harnessed by taking advantage of India's vast coastline. (b) State one advantage of using geothermal energy.",""),
(8,"ii",2,ME,"(a) How is Biogas formed? (b) Mention any one advantage of Biogas over other non-conventional energy resources.",""),
(8,"iii",3,ME,"Give a reason for each of the following. (a) Iron ore is called a versatile mineral. (b) Windmills set up on agricultural lands are beneficial to farmers. (c) Coal is the most preferred source of energy in Indian industries.",""),
(8,"iv",3,ME,"Study the picture given and answer: (a) Identify the type of energy being generated in the picture given above. (b) State why this type of energy is cheaper in the long run. (c) Name a power project associated with the generation of this energy in the northern part of India.","dam25"),
(9,"i",2,AG,"Mention two climatic conditions that favour the cultivation of groundnut.",""),
(9,"ii",2,AG,"Give any two reasons why Maharashtra has emerged as an important sugarcane producing state.",""),
(9,"iii",3,AG,"Give one reason to explain each of the following: (a) Trees are planted in between the rows of coffee plants. (b) Cotton cultivation requires plenty of cheap labour. (c) Hill slopes are best suited for tea cultivation.",""),
(9,"iv",3,AG,"Explain the following: (a) Mixed farming (b) Zayad (c) Transplantation",""),
(10,"i",2,IN,"State any two factors that are responsible for the growth of the cotton textile industry in Kolkata.",""),
(10,"ii",2,IN,"'Karnataka is the leading state for silk production in India'. Give any two reasons to justify the above statement.",""),
(10,"iii",3,IN,"(a) Name the Iron and Steel industry located at Chhattisgarh. (b) From where does the industry named by you above get its supply of the following? 1. Iron ore 2. Coal",""),
(10,"iv",3,IN,"Raghav has been given a project by his teacher in which he has to write about the by-products of an industry that is used for preparing shoe polish, carbon paper and cardboard. (a) Which industry will he be writing about? (b) Name any two by-products of the industry mentioned by you.",""),
(11,"i",2,TR,"Why is a well-developed transport network important for India?",""),
(11,"ii",2,TR,"Mention any two advantages of road transport.",""),
(11,"iii",3,TR,"Name the following: (a) The mode of transport that ensures comfortable journey, especially for elders and children. (b) The highway connecting Silchar in Assam to Porbandar in Gujarat. (c) The cheapest means of transport for bulky goods.",""),
(11,"iv",3,TR,"Give a reason for each of the following. (a) Airways are the most efficient mode of transport to connect Northeast India with the rest of the country. (b) Railways are easily developed in the Northern Plains of India. (c) Rivers of peninsular India are NOT ideal for inland water transport.",""),
(12,"i",2,WM,"(a) Give a reason for a substantial rise of E-waste in India. (b) What is dumping?",""),
(12,"ii",2,WM,"'You cannot protect environment unless you empower people, you inform them and help them to understand that these resources are their own, that they must protect them.' - Wangari Maathai (Nobel Prize 2004). As a responsible student how would you contribute to reduce and manage the waste generated in your surroundings. Explain by giving suitable examples.",""),
(12,"iii",3,WM,"With reference to the 3Rs, give a term that best describes each of the following: (a) An empty soft drink can is used as a pen stand. (b) Old scrap papers are used to manufacture handmade paper. (c) No food is wasted in the household.",""),
(12,"iv",3,WM,"Give a reason for the following statements: (a) Organic manure should replace chemical fertilisers. (b) There should be a ban on the use of polythene and plastic products. (c) Manual handling of waste must be avoided.",""),
]
