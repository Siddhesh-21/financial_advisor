$deprecationNote = @"
------------------------------------
`e[4mAction Required: AWS Tools V4 will be deprecated, upgrade to V5`e[0m
To avoid issues in the future, upgrade to AWS Tools V5 by performing the following:
Update your existing scripts and payloads, see guide: https://docs.aws.amazon.com/powershell/v5/userguide/migrating-v5.html
Update the environment variable and relaunch PowerShell.

export AWS_TOOLS_VERSION=V5

To learn more about environment variables, see https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html
------------------------------------
"@

if ($env:AWS_TOOLS_VERSION -eq "V5") {
    $env:PSModulePath = '/opt/microsoft/powershell/7/aws-tools-v5'
} else {
    Write-Host $deprecationNote
}

$PSStyle.OutputRendering = 'PlainText'
Register-ArgumentCompleter -Native -CommandName aws -ScriptBlock {
    param($commandName, $wordToComplete, $cursorPosition)
        $env:COMP_LINE=$wordToComplete
        $env:COMP_POINT=$cursorPosition
        aws_completer | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
        Remove-Item Env:\COMP_LINE     
        Remove-Item Env:\COMP_POINT    
}
Remove-Item Env:AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE -ErrorAction SilentlyContinue
Remove-Item Env:__MDE_ENV_API_AUTHORIZATION_TOKEN_FILE -ErrorAction SilentlyContinue
