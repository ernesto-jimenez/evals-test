package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
)

func main() {
	log.Println("eval mock on addr", os.Args)
	log.Println(http.ListenAndServe(
		os.Args[1],
		http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			switch r.URL.Path {
			case "", "/":
				if r.Method != http.MethodPost {
					http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
					return
				}

				err := runOpenAIEval(r, w)
				if err != nil {
					log.Printf("error /: %s\n", err)
					http.Error(w, err.Error(), http.StatusInternalServerError)
				}
			case "/dataset":
				if r.Method != http.MethodGet {
					http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
					return
				}

				err := json.NewEncoder(w).Encode(map[string]any{
					"data": []any{
						map[string]string{
							"input": "test-match",
						},
					},
				})
				if err != nil {
					log.Printf("error /dataset: %s\n", err)
					http.Error(w, err.Error(), http.StatusInternalServerError)
				}
			case "/assert":
				if r.Method != http.MethodPost {
					http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
					return
				}

				n, err := io.Copy(w, r.Body)
				if err != nil {
					log.Printf("error /assert: %s\n", err)
					if n == 0 {
						http.Error(w, err.Error(), http.StatusInternalServerError)
					}
				}

				if n == 0 {
					http.Error(w, "no data", http.StatusBadRequest)
				}
			default:
				log.Printf("unknown path: %s\n", r.URL.Path)
				http.Error(w, "not found", http.StatusNotFound)
			}
		}),
	))
}

func runOpenAIEval(r *http.Request, w http.ResponseWriter) error {
	var model string

	err := json.NewDecoder(r.Body).Decode(&model)
	if err != nil {
		return fmt.Errorf("error decoding request: %w", err)
	}

	output, err := os.CreateTemp(os.TempDir(), "eval-"+model)
	if err != nil {
		return fmt.Errorf("error creating temp file: %w", err)
	}
	defer os.Remove(output.Name())

	exec := exec.Command("./eval.sh", model)
	exec.Env = append(os.Environ(), "OAIEVAL_RECORD_PATH="+output.Name())
	exec.Stdout = os.Stdout
	exec.Stderr = os.Stderr

	err = exec.Run()
	if err != nil {
		return fmt.Errorf("error running eval: %w", err)
	}

	_, err = io.Copy(w, io.TeeReader(output, os.Stdout))
	if err != nil {
		return fmt.Errorf("error copying output: %w", err)
	}

	return nil
}
