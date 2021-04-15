import json
import time
#
#==>  read_cchdo_json.py (SCD: 2018.10.27)
#---------------------------------------------------------------------------
#==> script to read the output of CCHDO JSON from API 1.0 and turn filenames
#==> into 'curlable' entities for downloading (or whatever)
#---------------------------------------------------------------------------
#
#--> Set up base URL (for curl) input, output files and initialize data 
#--> structures
#
input_file = 'data.json'
cchdo_URL_prefix = 'https://cchdo.ucsd.edu'
output_filename = time.strftime("%Y%m%d")+"_"+time.strftime("%H%M%S")+"_get_files.sh"
curl_file_data = []

print "output file = ", output_filename
#
#--> open new output file
#
fileout = open(output_filename, 'w+')
fileout.write("#\n")

with open(input_file) as data_file:
	cruise_json = json.load(data_file)

print len(cruise_json['files']), "files" 
#
#--> turn each filename into a curlable object and append it to the array of files
#--> to be downloaded with curl
#
for cchdo_data_file in cruise_json['files'] :

	curlable_file =  ( cchdo_URL_prefix + cchdo_data_file['file_metadata']['file_path'])
	curl_file_data.append("curl -O " + curlable_file)

#
#--> end loop and write the command + data file URL to the output file with linefeeds
#
print "output array length is ",len(curl_file_data)
fileout.write ("\n".join(curl_file_data))
#
#--> Finally, close the output file
#
fileout.close()
