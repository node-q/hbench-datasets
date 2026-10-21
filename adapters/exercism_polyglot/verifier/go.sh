clean_workspace() {
  rm -f ./*_test.go go.work go.work.sum
}

run_tests() {
  GOTOOLCHAIN=local GOPROXY=off GOFLAGS= timeout 270 go test -count=1 .
}
