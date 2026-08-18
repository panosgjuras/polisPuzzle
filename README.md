# PolisPuzzle
Python toolkit for generating disaggregate travel-demand and transport-supply scenarios for MATSim, designed for cities across Greece.

<p align="center">
  <img src="logos/polisPuzzle-logo_v3.png" alt="#polisPuzzle logo" width="250">
</p>

## Links for socio-demographic data
Set of links with open demographic data from the 2021 census conducted by ELSTAT in Greece:

- [age vs education per municipality](https://www.statistics.gr/el/statistics?p_p_id=documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_cacheability=cacheLevelPage&p_p_col_id=column-2&p_p_col_count=4&p_p_col_pos=2&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_javax.faces.resource=document&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_ln=downloadResources&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_documentID=568511&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_locale=el)

- [gender vs age group vs employment (entire Greece)](https://www.statistics.gr/el/statistics?p_p_id=documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_cacheability=cacheLevelPage&p_p_col_id=column-2&p_p_col_count=4&p_p_col_pos=3&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_javax.faces.resource=document&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_ln=downloadResources&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_documentID=115986&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_locale=el)

- [education vs employment (entire Greece)](https://www.statistics.gr/el/statistics?p_p_id=documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_cacheability=cacheLevelPage&p_p_col_id=column-2&p_p_col_count=4&p_p_col_pos=3&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_javax.faces.resource=document&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_ln=downloadResources&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_documentID=115988&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_locale=el)

- [gender vs age group per settlement](https://www.statistics.gr/el/statistics?p_p_id=documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_cacheability=cacheLevelPage&p_p_col_id=column-2&p_p_col_count=4&p_p_col_pos=2&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_javax.faces.resource=document&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_ln=downloadResources&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_documentID=568507&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_locale=el)

- [gender vs education per settlement](https://www.statistics.gr/el/statistics?p_p_id=documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_cacheability=cacheLevelPage&p_p_col_id=column-2&p_p_col_count=4&p_p_col_pos=2&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_javax.faces.resource=document&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_ln=downloadResources&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_documentID=568504&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_locale=el)

- [gender vs age group vs education per region](https://www.statistics.gr/el/statistics?p_p_id=documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_cacheability=cacheLevelPage&p_p_col_id=column-2&p_p_col_count=4&p_p_col_pos=2&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_javax.faces.resource=document&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_ln=downloadResources&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_documentID=568518&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_locale=el)

- [employment (entire Greece)](https://www.statistics.gr/el/statistics?p_p_id=documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_cacheability=cacheLevelPage&p_p_col_id=column-2&p_p_col_count=4&p_p_col_pos=3&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_javax.faces.resource=document&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_ln=downloadResources&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_documentID=115986&_documents_WAR_publicationsportlet_INSTANCE_Mr0GiQJSgPHd_locale=el)

- [household vs number of cars per municipal unit](https://www.statistics.gr/el/statistics?p_p_id=documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_cacheability=cacheLevelPage&p_p_col_id=column-2&p_p_col_count=4&p_p_col_pos=2&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_javax.faces.resource=document&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_ln=downloadResources&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_documentID=532688&_documents_WAR_publicationsportlet_INSTANCE_VBZOni0vs5VJ_locale=el)

Socio-demographic characteristics are represented by the x- and y-variables, while the z-variable denotes the corresponding spatial unit. Five variables are utilize to tag an agent: gender, age group, education, employment and car count.

## Modules

 - Module 1. [diary_prep](): Process travel diaries and identify activity–travel patterns using hierarchical clustering;

 - Module 2. [pop_synthesis](https://github.com/panosgjuras/polisPuzzle/tree/main/src/polispuzzle/pop_synthesis): Generate synthetic people and households with specified sociodemographic characteristics;

 - Module 3. [diary_expand](): Reproduce and expand plans directly from observed diaries, without synthetic pattern assignment;

 - Module 4. [plan_assign](): Match synthetic travellers to representative clusters and assign daily plans;

 - Module 5. [road_net](https://github.com/panosgjuras/polisPuzzle/tree/main/src/polispuzzle/road_net): Download, clean, transform, and export road networks for MATSim;

 - Module 6. [pt_net](): Process GTFS feeds or import existing transit schedules for MATSim

 - Module 7. [od_assign](): Assign precise activity locations and trip origins/destinations beyond zonal representations

 - Module 8. [matsim](): responsible for converting those objects into MATSim files. This prevents MATSim-specific XML details from spreading through every module.
