# Lyman
Lyman is a graphical user interface (GUI) designed to simplify the process of creating cstruct files. It eliminates the need to remember the correct formatting of cstruct files, as Lyman manages that automatically. Users simply fill out a form, and Lyman handles the rest. If any required information is missing, Lyman will highlight the omission and prevent the cstruct file from being saved until all necessary details are provided.

Another challenge with writing cstruct files lies in the log files themselves. To write a cstruct file, it is necessary to view the raw log entry, which can be difficult if the file is gzipped (compressed). Uncompressing the log requires an understanding of the log format, the removal of the header, and the uncompressing of the log data. Additionally, it is important to know how to identify the start and end of the specific log entry of interest.

This is where Lyman becomes invaluable. Lyman manages all these complexities, allowing users to focus on finding data rather than deciphering the intricacies of the log file format. By using Lyman, a more robust solution for parsing OneDrive logs can be developed, contributing back to the ODEFiles repository [Beercow/ODEFiles (github.com)](https://github.com/Beercow/ODEFiles).

