# Autocomplete of CLI's Subcommands and Parameters

The source code for Wordfence CLI [comes with a script](../scripts/) that can be used to automatically suggest or fill in subcommands and command line parameters. To use these autocompletions from `bash`, you can run `source ./scripts/complete.bash` from the base of the source code directory. If you are using `zsh`, you can run the following prior to running `source` on the bash completion file:

	autoload -Uz +X compinit && compinit
	autoload -Uz +X bashcompinit && bashcompinit

Once this is done, you can use the `Tab` key to suggest subcommands or parameters when running `wordfence` from the command line.

## Examples

	$ source wordfence-cli/scripts/complete.bash 
	$ wordfence vuln-scan -
	--accept-terms              -E                          -l                          --no-debug                  --output                    --quiet                     --smtp-user
	--banner                    --email                     -L                          --no-help                   --output-columns            --read-stdin                -t
	-c                          --email-from                --license                   --no-informational          --output-format             --relative-content-path     --theme-directory
	-C                          --exclude-vulnerability     --log-level                 --no-output                 --output-headers            --relative-mu-plugins-path  -v
	--cache                     -f                          -m                          --no-output-headers         --output-path               --relative-plugins-path     --verbose
	--cache-directory           --feed                      -M                          --no-prefix-log-levels      -p                          --require-path              --version
	--check-for-update          -h                          --no-accept-terms           --no-purge-cache            -P                          -s                          -w
	--color                     --help                      --no-banner                 --no-quiet                  --path-separator            --sendmail-path             --wfi-url
	--configuration             -i                          --noc1-url                  --no-read-stdin             --plugin-directory          --smtp-host                 --wordpress-path
	-d                          -I                          --no-cache                  --no-require-path           --prefix-log-levels         --smtp-password             
	--debug                     --include-vulnerability     --no-check-for-update       --no-verbose                --purge-cache               --smtp-port                 
	-e                          --informational             --no-color                  --no-version                -q                          --smtp-tls-mode             

<!-- -->
	
	$ wordfence malware-scan -
	-a                       --debug                  --images                 -n                       --no-include-all-files   --output-columns         -s                       --wfi-url
	--accept-terms           -e                       --include-all-files      -N                       --no-match-all           --output-format          --scanned-content-limit  --workers
	--allow-io-errors        -E                       --include-files          --no-accept-terms        --no-output              --output-headers         --sendmail-path          -x
	--banner                 --email                  --include-files-pattern  --no-allow-io-errors     --no-output-headers      --output-path            --smtp-host              -X
	-c                       --email-from             --include-signatures     --no-banner              --no-prefix-log-levels   --pcre-backtrack-limit   --smtp-password          -z
	--cache                  --exclude-files          -l                       --noc1-url               --no-progress            --pcre-recursion-limit   --smtp-port              
	--cache-directory        --exclude-files-pattern  -L                       --no-cache               --no-purge-cache         --prefix-log-levels      --smtp-tls-mode          
	--check-for-update       --exclude-signatures     --license                --no-check-for-update    --no-quiet               --progress               --smtp-user              
	--chunk-size             --file-list-separator    --log-level              --no-color               --no-read-stdin          --purge-cache            -v                       
	--color                  -h                       -m                       --no-debug               --no-verbose             -q                       --verbose                
	--configuration          --help                   -M                       --no-help                --no-version             --quiet                  --version                
	-d                       -i                       --match-all              --no-images              --output                 --read-stdin             -w                       
	